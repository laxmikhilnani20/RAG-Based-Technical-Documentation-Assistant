# System Architecture
# RAG-Based Technical Documentation Assistant

> **Version:** 1.0.0
> **Last Updated:** May 2025
> **Stack:** Python 3.11 · LangGraph · FastAPI · ChromaDB · Google Gemini

---

## 1. Overview

The RAG-Based Technical Documentation Assistant is a self-corrective,
retrieval-augmented generation (RAG) system that answers natural language
questions about technical documentation.

The system is built around a **LangGraph StateGraph** — a directed graph where
each node performs a specific task (query analysis, retrieval, grading,
generation), and conditional edges route the flow based on intermediate results.
The graph is served as a REST API via **FastAPI** and deployed as a Docker
container on **Hugging Face Spaces**.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER / CLIENT                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP Request (POST /query)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Layer                               │
│   /query   /ingest   /documents   /feedback                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Invokes
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LangGraph StateGraph                           │
│                                                                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │    Node 1    │────▶│    Node 2    │────▶│    Node 3    │   │
│   │Query Analysis│     │  Retrieval   │     │  Doc Grading │   │
│   └──────────────┘     └──────────────┘     └──────┬───────┘   │
│                                                     │           │
│                          ┌──────────────────────────┤           │
│                          │                          │           │
│                    relevant ✅                 irrelevant ❌    │
│                          │                          │           │
│                          ▼                          ▼           │
│                   ┌──────────────┐         ┌──────────────┐    │
│                   │    Node 4    │         │  Retry Logic │    │
│                   │  Generation  │         │ (max 2 tries)│    │
│                   └──────┬───────┘         └──────┬───────┘    │
│                          │                        │             │
│                          │                   rewrite query      │
│                          │                        │             │
│                          │                        └──▶ Node 2   │
│                          │                   (or "I don't know")│
└──────────────────────────┼────────────────────────────────────-─┘
                           │ Answer + Citations
                           ▼
                     HTTP Response
```

---

## 3. LangGraph Workflow — Node by Node

### State Schema

Before the nodes, we define the **state** — the data that flows between every node:

```python
class RAGState(TypedDict):
    question: str               # Original user question
    rewritten_query: str        # Query after analysis/rewrite
    query_type: str             # conceptual | how-to | troubleshooting | api-ref
    retrieved_docs: list        # Raw chunks from ChromaDB
    graded_docs: list           # Filtered relevant chunks only
    generation: str             # Final answer text
    citations: list             # Source references
    retry_count: int            # Tracks retry attempts (max: 2)
    answer_found: bool          # Whether we found a valid answer
    session_id: str             # Session identifier — reserved for conversation memory (future use)
```

---

### Node 1: Query Analysis

**Purpose:** Prepare the raw user question for retrieval.

**What it does:**
- Rewrites the query to be more specific and retrieval-friendly
  - e.g., *"how do I use it?"* → *"how to use LangGraph StateGraph in Python?"*
- Classifies the query type into one of four categories:
  - `conceptual` — "What is LangGraph?"
  - `how-to` — "How do I add memory to a LangGraph agent?"
  - `troubleshooting` — "Why is my ChromaDB collection empty?"
  - `api-reference` — "What parameters does `add_edge()` accept?"
- The query type can guide downstream generation style

**Input:** `question`
**Output:** `rewritten_query`, `query_type`
**LLM Used:** Gemini 1.5 Flash

---

### Node 2: Retrieval

**Purpose:** Find the most relevant document chunks from the vector store.

**What it does:**
- Takes the `rewritten_query` and converts it to an embedding vector
  using Gemini `text-embedding-004`
- Performs cosine similarity search in ChromaDB
- Returns the **top-k chunks** (default: 5) along with source metadata
  (document name, page number, URL)

**Input:** `rewritten_query`
**Output:** `retrieved_docs` (list of chunks + metadata)
**Model Used:** Gemini `text-embedding-004` (embedding)
**Store:** ChromaDB (local persistent vector store)

---

### Node 3: Document Grading

**Purpose:** Self-corrective filtering — ensure retrieved docs are actually relevant.

**What it does:**
- Sends each retrieved chunk to Gemini with a grading prompt:
  *"Is this document relevant to the question? Answer YES or NO."*
- Filters out all chunks graded as irrelevant
- Counts how many relevant chunks remain:
  - If **≥ 1 relevant** → proceed to Generation
  - If **0 relevant** → trigger retry logic

**Retry Logic (Conditional Edge):**
- Increments `retry_count`
- If `retry_count < MAX_RETRY_ATTEMPTS (2)`:
  - Rewrites the query differently → loops back to Node 2
- If `retry_count >= 2`:
  - Sets `answer_found = False`
  - Returns a graceful *"I don't have enough information..."* response

**Input:** `retrieved_docs`, `question`
**Output:** `graded_docs`, routing decision
**LLM Used:** Gemini 1.5 Flash

---

### Node 4: Generation

**Purpose:** Generate the final grounded answer using relevant context.

**What it does:**
- Constructs a prompt with:
  - The user's original question
  - All graded (relevant) document chunks as context
  - Instructions to cite sources
- Calls Gemini 1.5 Flash to generate a clear, accurate answer
- Extracts citations from the source metadata of used chunks
- Returns the answer + list of source references

**Input:** `graded_docs`, `question`
**Output:** `generation` (answer text), `citations`
**LLM Used:** Gemini 1.5 Flash

---

## 4. Conditional Routing Logic

```
After Node 3 (Grading):

  graded_docs is not empty?
  │
  ├── YES ──▶ route_to_generation()  ──▶ Node 4
  │
  └── NO  ──▶ retry_count < 2?
              │
              ├── YES ──▶ rewrite_query() ──▶ Node 2 (retry)
              │
              └── NO  ──▶ end (return "I don't know" response)
```

This is implemented as a `conditional_edge` in LangGraph, which evaluates a
routing function after Node 3 completes.

---

## 5. Document Ingestion Pipeline

This runs **before** the LangGraph workflow — either at startup or via the
`POST /ingest` endpoint.

```
Source Documents (URLs / Files)
        │
        ▼
  Document Loader
  (LangChain WebBaseLoader / PyPDFLoader)
        │
        ▼
  Text Splitter
  (RecursiveCharacterTextSplitter)
  chunk_size=1000, chunk_overlap=200
        │
        ▼
  Embedding Model
  (Gemini text-embedding-004)
        │
        ▼
  ChromaDB Vector Store
  (Persisted locally at ./chroma_db)
```

### Document Corpus

| # | Source | Type | Why Chosen |
|---|--------|------|------------|
| 1 | LangChain Docs | Web (HTML) | Core framework used in the pipeline |
| 2 | LangGraph Docs | Web (HTML) | Graph workflow engine — central to architecture |
| 3 | FastAPI Docs | Web (HTML) | API layer — directly used in this project |

---

## 6. Technology Stack

| Layer | Technology | Why Chosen |
|-------|-----------|------------|
| **LLM** | Google Gemini 1.5 Flash | Free tier, fast inference, handles both LLM + embeddings from one API key |
| **Embeddings** | Gemini `text-embedding-004` | State-of-the-art quality, no extra provider needed |
| **Graph Workflow** | LangGraph `StateGraph` | Built for agentic RAG — native support for conditional edges, retry loops, state management |
| **Vector Store** | ChromaDB | Simple, local, open-source, zero infrastructure required |
| **API Framework** | FastAPI | Async, fast, auto-generates OpenAPI docs, industry standard |
| **Containerization** | Docker | Reproducible environments, HF Spaces compatible |
| **Deployment** | Hugging Face Spaces (Docker SDK) | Free hosting, Docker native, public URL |
| **Language** | Python 3.11 | Latest stable, best LangChain/LangGraph support |

---

## 7. FastAPI ↔ LangGraph Integration

```
FastAPI receives POST /query
        │
        ▼
Validates request (Pydantic model)
        │
        ▼
Builds initial RAGState:
  { question: "...", retry_count: 0, ... }
        │
        ▼
graph.invoke(state)  ← runs the full LangGraph workflow
        │
        ▼
Returns: { answer: "...", sources: [...], query_type: "..." }
```

---

## 8. Project Folder Structure

```
RAG-Based Technical Documentation Assistant/
│
├── app/                          ← FastAPI + LangGraph application
│   ├── main.py                   ← FastAPI app entry point
│   ├── config.py                 ← Settings loaded from .env
│   ├── graph/
│   │   ├── state.py              ← RAGState TypedDict definition
│   │   ├── nodes.py              ← All 4 LangGraph node functions
│   │   ├── edges.py              ← Conditional routing functions
│   │   └── workflow.py           ← StateGraph assembly
│   ├── api/
│   │   ├── routes/
│   │   │   ├── query.py          ← POST /query
│   │   │   ├── ingest.py         ← POST /ingest
│   │   │   ├── documents.py      ← GET /documents
│   │   │   └── feedback.py       ← POST /feedback
│   │   └── models.py             ← Pydantic request/response models
│   ├── rag/
│   │   ├── embeddings.py         ← Gemini embedding wrapper
│   │   ├── vector_store.py       ← ChromaDB operations
│   │   └── ingestion.py          ← Document loading & chunking
│   └── utils/
│       └── logger.py             ← Loguru logger setup
│
├── docs_corpus/                  ← Raw source documents (fetched at startup)
├── chroma_db/                    ← Persisted ChromaDB vector store
├── docs/                         ← Project documentation (this folder)
│   ├── architecture.md           ← THIS FILE
│   ├── api-spec.md
│   ├── corpus-strategy.md
│   ├── design-decisions.md
│   └── project-structure.md
│
├── scripts/
│   └── ingest_docs.py            ← Standalone ingestion script
│
├── .env                          ← Secrets (gitignored)
├── .env.example                  ← Template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 9. Data Flow Summary

```
1. User sends: POST /query { "question": "How do I add memory to LangGraph?" }

2. FastAPI validates → builds initial RAGState

3. Node 1 (Query Analysis):
   → Rewrites: "LangGraph memory management add_messages checkpointer"
   → Type: "how-to"

4. Node 2 (Retrieval):
   → Embeds rewritten query with Gemini text-embedding-004
   → Searches ChromaDB → returns top 5 chunks from LangGraph docs

5. Node 3 (Grading):
   → Gemini grades each chunk: [YES, YES, NO, YES, NO]
   → Keeps 3 relevant chunks → proceed to generation

6. Node 4 (Generation):
   → Gemini generates answer grounded in 3 chunks
   → Attaches source citations

7. FastAPI returns:
   {
     "answer": "To add memory in LangGraph, use a checkpointer...",
     "sources": ["langgraph.com/docs/...", "..."],
     "query_type": "how-to",
     "retry_count": 0
   }
```

---

*All other documents in this `docs/` folder reference this architecture as the source of truth.*
