# RAG-Based Technical Documentation Assistant
### Express Analytics — AI/ML Engineer Intern Take-Home Assignment

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6B35?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-6B3FA0?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)

> **Live Demo:** [huggingface.co/spaces/IDKwhatiscorrect/RAG-Based-Technical-Documentation-Assistant](https://huggingface.co/spaces/IDKwhatiscorrect/RAG-Based-Technical-Documentation-Assistant)

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Assignment Requirements — Fulfilled](#2-assignment-requirements--fulfilled)
3. [System Architecture](#3-system-architecture)
4. [LangGraph Workflow (4 Nodes + Conditional Edges)](#4-langgraph-workflow)
5. [Document Ingestion Pipeline](#5-document-ingestion-pipeline)
6. [API Reference](#6-api-reference)
7. [Bonus Features Implemented](#7-bonus-features-implemented)
8. [Setup & Running Locally](#8-setup--running-locally)
9. [Running with Docker](#9-running-with-docker)
10. [Deployment on Hugging Face Spaces](#10-deployment-on-hugging-face-spaces)
11. [Design Decisions & Tradeoffs](#11-design-decisions--tradeoffs)
12. [Chunking & Embedding Strategy](#12-chunking--embedding-strategy)
13. [What I Would Improve With More Time](#13-what-i-would-improve-with-more-time)
14. [Assumptions Made](#14-assumptions-made)
15. [Project Structure](#15-project-structure)

---

## 1. Project Overview

This is a production-grade **Retrieval-Augmented Generation (RAG)** system that answers technical questions using real documentation as its knowledge base. Instead of relying on an LLM's stale training data, the system:

1. Fetches and indexes documentation from official sources (LangGraph, LangChain, FastAPI)
2. Embeds questions and searches ChromaDB for the most semantically similar chunks
3. **Grades** every retrieved chunk for relevance — irrelevant chunks are discarded
4. **Automatically rewrites the query and retries** if no relevant chunks are found (self-corrective loop)
5. Generates a grounded, cited answer using only verified context

The key differentiator is the **self-corrective agentic loop** powered by **LangGraph StateGraph** — making this a true agentic RAG system, not a simple one-shot chain.

---

## 2. Assignment Requirements — Fulfilled

| Requirement | Status | Where Implemented |
|---|:---:|---|
| LangGraph `StateGraph` with 4 nodes | ✅ | `app/graph/workflow.py`, `app/graph/nodes.py` |
| Node 1: Query Analysis (rewrite + classify) | ✅ | `analyze_query()` in `nodes.py` |
| Node 2: Retrieval from vector store | ✅ | `retrieve_docs()` in `nodes.py` |
| Node 3: Document Grading (relevant/irrelevant) | ✅ | `grade_documents()` in `nodes.py` |
| Node 4: Generation with citations | ✅ | `generate_answer()` in `nodes.py` |
| Conditional edges routing on grading outcome | ✅ | `route_after_grading()` in `edges.py` |
| Retry loop with retry limit | ✅ | Max 2 retries, tracked in `RAGState.retry_count` |
| Fallback when retries exhausted | ✅ | Graceful "I don't know" in `generate_answer()` |
| Document ingestion pipeline | ✅ | `app/rag/ingestion.py` |
| Load from URLs | ✅ | `WebBaseLoader` in `ingestion.py` |
| Load from files (PDF) | ✅ | `PyPDFLoader` in `ingestion.py` |
| Chunk with overlap strategy | ✅ | `RecursiveCharacterTextSplitter` |
| Generate embeddings | ✅ | `gemini-embedding-2` via `embeddings.py` |
| Store in ChromaDB | ✅ | `app/rag/vector_store.py` |
| `POST /query` endpoint | ✅ | `app/api/routes/query.py` |
| `POST /ingest` endpoint (URLs) | ✅ | `app/api/routes/ingest.py` |
| `POST /ingest/file` endpoint (PDF upload) | ✅ | `app/api/routes/ingest.py` |
| `GET /documents` endpoint | ✅ | `app/api/routes/documents.py` |
| `POST /feedback` endpoint | ✅ | `app/api/routes/feedback.py` |
| Error handling & input validation | ✅ | Pydantic models + HTTP status codes |
| README with architecture + setup + examples | ✅ | This file |
| Design decisions write-up | ✅ | [Section 11](#11-design-decisions--tradeoffs) |
| Corpus or fetch script | ✅ | `scripts/ingest_docs.py` |
| Chunking/embedding strategy explained | ✅ | [Section 12](#12-chunking--embedding-strategy) |
| **Bonus:** Simple UI | ✅ | Full glassmorphism chat UI (beyond Streamlit/Gradio) |
| **Bonus:** Session ID for follow-ups | ✅ | `session_id` in `RAGState` |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                BROWSER (Chat UI)                        │
│  HTML + CSS (glassmorphism) + Vanilla JS                │
│  • User types question                                  │
│  • Gemini API key passed via x-api-key header (BYOK)    │
│  • Responses rendered as Markdown                       │
│  • Citations as clickable badges                        │
│  • Thumbs up/down feedback per answer                   │
│  • PDF upload panel for custom documents                │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /query  (x-api-key header)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Application                       │
│  Routes: /query  /ingest  /ingest/file                  │
│          /documents  /feedback  /health                 │
│  Serves static UI at GET /                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│           LangGraph StateGraph (RAGState)               │
│                                                         │
│  analyze_query → retrieve_docs → grade_documents        │
│                                        │                │
│                          ┌─────────────┴────────┐       │
│                          │  route_after_grading  │       │
│                          └──────┬────────┬───────┘       │
│                    docs found   │        │ no docs        │
│                                 │        │ + retry < 2   │
│                    generate_    │        │ rewrite_query  │
│                    answer       │        │ → retrieve     │
│                    (with        │        │ (retry loop)   │
│                    citations)   │        │                │
│                                 │  no docs + retries     │
│                                 │  exhausted → fallback  │
└─────────────────────────────────────────────────────────┘
                       │                │
              ┌────────┘                └────────┐
              ▼                                  ▼
┌─────────────────────┐            ┌────────────────────────┐
│  ChromaDB           │            │  Google Gemini API      │
│  Persistent vector  │            │  LLM: gemini-3.1-      │
│  store              │            │    flash-lite           │
│  Collection:        │            │  Embeddings:            │
│    technical_docs   │            │    gemini-embedding-2   │
│  Top-K = 2          │            │                        │
└─────────────────────┘            └────────────────────────┘
```

---

## 4. LangGraph Workflow

### State Schema (`app/graph/state.py`)

The `RAGState` TypedDict flows between all nodes:

```python
class RAGState(TypedDict):
    question: str           # Original user question
    rewritten_query: str    # Query after analysis/rewrite
    query_type: str         # conceptual | how-to | troubleshooting | api-reference
    retrieved_docs: List    # Raw chunks from ChromaDB
    graded_docs: List       # Filtered relevant chunks only
    generation: str         # Final answer text
    citations: List[Dict]   # Source references with URL + preview
    retry_count: int        # Tracks retry attempts (max: 2)
    answer_found: bool      # Whether a valid answer was found
    session_id: Optional[str]
    api_key: Optional[str]  # User-provided BYOK key
```

---

### Node 1 — `analyze_query` ✅

**File:** `app/graph/nodes.py`

Takes the raw user question and prepares it for retrieval. Uses `llm.with_structured_output()` to guarantee valid JSON output:

```python
class QueryAnalysisOutput(BaseModel):
    rewritten_query: str  # Optimized for vector search
    query_type: str       # conceptual | how-to | troubleshooting | api-reference
```

The rewritten query removes ambiguity, adds relevant synonyms, and focuses on technical terms that will match embeddings well. The query type is also used in the API response to help users understand how the system interpreted their question.

---

### Node 2 — `retrieve_docs` ✅

**File:** `app/graph/nodes.py`

Embeds the rewritten query using `gemini-embedding-2` and searches ChromaDB for the top-K=2 most semantically similar chunks.

```python
retriever = get_retriever(api_key)
docs = retriever.invoke(rewritten_query)
```

---

### Node 3 — `grade_documents` ✅

**File:** `app/graph/nodes.py`

Each retrieved chunk is individually graded by the LLM using structured output:

```python
class GraderOutput(BaseModel):
    is_relevant: str  # "yes" or "no"
```

The grader prompt asks the LLM whether the chunk contains keywords or semantic meaning related to the question. Only "yes" chunks pass through to generation. This prevents hallucination from irrelevant context.

---

### Node 4 — `generate_answer` ✅

**File:** `app/graph/nodes.py`

Generates the final answer using **only** the graded relevant documents as context. If `graded_docs` is empty (exhausted retries), the node emits a graceful fallback:

> *"I don't have enough information in my knowledge base to answer this question accurately..."*

When docs are available, the prompt instructs the LLM to:
- Answer **only** from the provided context
- Say "I don't know" if context is insufficient
- Cite sources naturally in the response

Citations are extracted from chunk metadata (source URL + 150-char preview).

---

### Conditional Edges — `route_after_grading` ✅

**File:** `app/graph/edges.py`

```python
def route_after_grading(state) -> Literal["generate_answer", "rewrite_query", "fallback_answer"]:
    graded_docs = state.get("graded_docs", [])
    retry_count = state.get("retry_count", 0)

    if len(graded_docs) > 0:
        return "generate_answer"           # ✅ Relevant docs found

    if retry_count < settings.MAX_RETRY_ATTEMPTS:  # MAX = 2
        return "rewrite_query"             # 🔄 Retry with new query

    return "generate_answer"               # 🛑 Exhausted — fallback
```

### Node 5 — `rewrite_query` (Retry Loop) ✅

When grading fails, this node completely reformulates the query with different phrasing, synonyms, and broader concepts. It increments `retry_count` and routes back to `retrieve_docs`, creating a self-corrective loop.

**Graph topology:**
```
analyze_query → retrieve_docs → grade_documents
                     ↑                 ↓ (conditional)
                rewrite_query ←────────┘  (if no docs + retry < 2)
                                          ↓ (if docs found)
                                    generate_answer → END
```

---

## 5. Document Ingestion Pipeline

**File:** `app/rag/ingestion.py`

### Pipeline Steps

```
1. Load                          2. Split
WebBaseLoader (URLs)     →   RecursiveCharacterTextSplitter
PyPDFLoader   (PDFs)         chunk_size=1000, overlap=200

3. ID Generation               4. Embed + Store
MD5(source_url + index)  →   gemini-embedding-2
Deterministic upserts         ChromaDB.add_documents(ids=...)
```

### Default Corpus (`scripts/ingest_docs.py`)

4 URLs from official documentation (chosen to stay under Gemini free-tier rate limits):

| # | URL | Topic |
|---|-----|-------|
| 1 | `langchain-ai.github.io/langgraph/concepts/low_level/` | LangGraph low-level API |
| 2 | `langchain-ai.github.io/langgraph/concepts/high_level/` | LangGraph high-level concepts |
| 3 | `python.langchain.com/docs/concepts/rag/` | LangChain RAG concepts |
| 4 | `fastapi.tiangolo.com/tutorial/first-steps/` | FastAPI basics |

Users can also ingest their own URLs via `POST /ingest` or upload PDFs via the UI.

---

## 6. API Reference

### `POST /query` ✅

```http
POST /query
Content-Type: application/json
x-api-key: <YOUR_GEMINI_API_KEY>

{
  "question": "How does LangGraph handle state management?",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "answer": "LangGraph manages state using a TypedDict...",
  "sources": [
    {
      "document": "https://langchain-ai.github.io/langgraph/concepts/low_level/",
      "url": "https://langchain-ai.github.io/langgraph/concepts/low_level/",
      "chunk_preview": "LangGraph provides a StateGraph abstraction..."
    }
  ],
  "query_type": "conceptual",
  "retries_used": 0,
  "session_id": "a1b2c3..."
}
```

---

### `POST /ingest` ✅ — Ingest URLs

```http
POST /ingest
Content-Type: application/json
x-api-key: <YOUR_GEMINI_API_KEY>

{
  "urls": ["https://python.langchain.com/docs/concepts/rag/"]
}
```

**Response:**
```json
{
  "status": "success",
  "documents_ingested": 1,
  "chunks_created": 42,
  "collection": "technical_docs",
  "message": "Successfully ingested 1 documents into 42 chunks."
}
```

---

### `POST /ingest/file` ✅ — Upload PDF

```http
POST /ingest/file
Content-Type: multipart/form-data
x-api-key: <YOUR_GEMINI_API_KEY>

file: <PDF binary>
```

---

### `GET /documents` ✅ — List Indexed Chunks

```http
GET /documents?limit=20&offset=0

Response:
{
  "total_chunks": 156,
  "chunks": [
    {
      "id": "a3f2b1...",
      "content_preview": "LangGraph is a library for building...",
      "metadata": { "source": "https://...", "chunk_index": 0 }
    }
  ]
}
```

---

### `POST /feedback` ✅ — Submit Rating

```http
POST /feedback
Content-Type: application/json

{
  "query_id": "session-uuid",
  "rating": "up",
  "comment": "Very helpful!"
}
```

Feedback is appended to `feedback.jsonl` on disk for analysis.

---

### `GET /health` — Health Check

```http
GET /health
→ { "status": "ok", "environment": "development" }
```
Required for Docker and HF Spaces health monitoring.

---

## 7. Bonus Features Implemented

| Bonus Feature | Status | Notes |
|---|:---:|---|
| Simple UI | ✅ **Exceeded** | Full production glassmorphism chat UI — not just Streamlit/Gradio |
| Session ID tracking | ✅ | `session_id` generated per conversation for future memory |
| PDF upload via UI | ✅ | Sidebar PDF upload panel — beyond the base requirement |
| BYOK (Bring Your Own Key) | ✅ | API key never stored server-side; passed per-request |
| Conversation memory | 🔶 Partial | `session_id` reserved in state; full memory not yet wired |
| Hallucination check | ❌ | Not implemented; would add as a 5th graph node |
| Web search fallback | ❌ | Not implemented; would integrate Tavily as a 6th node |

---

## 8. Setup & Running Locally

### Prerequisites
- Python 3.11+
- A free Google Gemini API key → [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/RAG-Based-Technical-Documentation-Assistant.git
cd "RAG-Based Technical Documentation Assistant"

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file (no edits needed — key is per-request via UI)
cp .env.example .env

# 5. Populate the vector store (first run only)
python scripts/ingest_docs.py
# ⚠️ This requires your Gemini API key set as env var:
# export GEMINI_API_KEY=your_key_here  (only for the script)

# 6. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** → paste your Gemini API key in the sidebar → start asking questions.

---

## 9. Running with Docker

```bash
# Start
docker compose up --build

# Stop
docker compose down

# Logs
docker compose logs -f

# Restart after config change
docker compose restart
```

Available at **http://localhost:8000**. ChromaDB data persists in a named Docker volume (`chroma_data`) across restarts.

---

## 10. Deployment on Hugging Face Spaces

The app is deployed as a **Docker Space** on HF. Port `7860` is mandatory for HF Spaces Docker SDK — the `Dockerfile` uses this port while `docker-compose.yml` maps `8000:7860` for local dev.

**Deploy steps:**
1. Push code to a public GitHub repo
2. Create new Space → select **Docker** SDK
3. Link your GitHub repo
4. HF Spaces auto-builds on every push to `main`

The `chroma_db/` directory is committed to the repo and baked into the Docker image, so the vector store is available immediately on boot — no re-ingestion needed after deployment.

---

## 11. Design Decisions & Tradeoffs

### Why LangGraph instead of a simple LangChain chain?

A standard `LLMChain` is **linear** — it cannot loop back. LangGraph's `StateGraph` enables **cyclical, conditional routing**, which is essential for the retry loop. When grading fails, we can route back to `rewrite_query → retrieve_docs` and try again. This makes the system genuinely self-corrective rather than a best-effort single-pass.

**Tradeoff:** LangGraph adds complexity and a steeper learning curve. For simple Q&A with no retry logic, a chain would be sufficient.

### Why ChromaDB over FAISS?

ChromaDB offers **persistent storage** with zero additional infrastructure — it writes data to disk via `PersistentClient`. FAISS is in-memory by default and requires manual serialization/deserialization. For a containerized deployment where data must survive restarts, ChromaDB's persistence is a significant advantage.

**Tradeoff:** ChromaDB is slower than FAISS for very large datasets (millions of vectors). For this corpus size (hundreds of chunks), the difference is negligible.

### Why deterministic chunk IDs?

```python
chunk_id = MD5(source_url + chunk_index)
```

Using content-derived IDs means re-ingesting the same URL **upserts** (overwrites) existing chunks rather than creating duplicates. The ingestion pipeline is idempotent — safe to run repeatedly without bloating the database.

**Tradeoff:** If a document's content changes significantly, the same ID is reused but the content is updated. This is usually desirable.

### Why structured outputs for grading and query analysis?

`llm.with_structured_output(PydanticModel)` guarantees the LLM returns a valid, schema-conformant JSON object. Without this, we'd need fragile regex/string parsing to extract `"yes"` or `"no"` from a free-form response. Structured outputs make the pipeline **robust to prompt variation**.

### Why BYOK (Bring Your Own Key)?

The Gemini free tier has a 15 RPM (requests per minute) limit. Sharing one server-side key across all users would exhaust it immediately. With BYOK, each user's quota is independent. The API key is passed via the `x-api-key` header per request, flows through the LangGraph state, and is used directly with the Gemini SDK — it is **never logged or persisted**.

### Why Gemini 3.1 Flash Lite as the LLM?

- GA as of May 7, 2026 — production-stable
- Fastest and most cost-efficient in the Gemini 3 series
- Supports `with_structured_output()` — critical for the grader and query analyzer nodes
- Free tier available (up to 15 RPM / 1M TPM)

---

## 12. Chunking & Embedding Strategy

### Chunking

```
Strategy: RecursiveCharacterTextSplitter
Chunk size:    1000 characters
Chunk overlap: 200 characters
Separators:    ["\n\n", "\n", " ", ""]
```

**Why 1000 chars?** Technical documentation has dense, self-contained paragraphs. 1000 characters (~200-250 tokens) is large enough to preserve a complete concept but small enough to remain specific. Smaller chunks (e.g., 300 chars) fragment sentences and lose context; larger chunks (e.g., 3000 chars) dilute the semantic signal and make retrieval less precise.

**Why 200-char overlap?** Ensures that sentences straddling chunk boundaries are captured in both adjacent chunks. This prevents answers from falling into a gap between two chunks.

**Why `RecursiveCharacterTextSplitter`?** It tries to split at natural boundaries (`\n\n` → paragraph, `\n` → line, ` ` → word) before falling back to character splits. This preserves semantic integrity better than a fixed-character splitter.

### Embeddings

```
Model: models/gemini-embedding-2
Provider: Google Generative AI
```

`gemini-embedding-2` is Google's state-of-the-art embedding model optimized for semantic similarity. It produces high-dimensional vectors that capture nuanced technical meaning — particularly important for distinguishing between concepts like "LangGraph nodes" vs "LangGraph edges" which share many surface-level tokens.

---

## 13. What I Would Improve With More Time

1. **Hallucination check node** — Add a 5th LangGraph node after generation that verifies the answer is actually supported by the retrieved context (inspired by Self-RAG). Route back to regeneration if the answer contradicts the sources.

2. **Web search fallback** — Integrate Tavily as a 6th node. If the vector store has no relevant results after max retries, fall back to a live web search before emitting the fallback answer.

3. **Full conversation memory** — Wire the `session_id` into a Redis or in-memory store to maintain chat history, enabling follow-up questions like "Can you explain that differently?"

4. **Streaming responses** — Use FastAPI `StreamingResponse` + LangChain streaming to show the answer token-by-token in the UI rather than waiting for the full response.

5. **Larger, richer corpus** — Expand to cover more pages of LangGraph, LangChain, and FastAPI docs. Currently limited to 4 URLs to stay within free-tier rate limits.

6. **Query type-based routing** — Use the `query_type` from Node 1 to adapt retrieval strategy (e.g., for `api-reference` queries, increase top-K; for `conceptual`, reduce it).

7. **Evaluation pipeline** — Add a RAGAS evaluation framework to measure faithfulness, answer relevancy, and context precision automatically.

---

## 14. Assumptions Made

1. **BYOK is acceptable** — The assignment doesn't specify how the API key is managed. BYOK was chosen over a server-side key to avoid rate-limit exhaustion and to keep the deployment cost-free.

2. **ChromaDB persisted to disk** — Assumed persistent storage is required between requests. An in-memory store would reset on every container restart.

3. **4 corpus URLs is sufficient** — The assignment says "3–5 documents". Chose 4 URLs covering all three technologies to demonstrate cross-domain retrieval.

4. **`source` metadata as URL** — The `WebBaseLoader` sets `metadata["source"]` to the page URL. This is used directly as the citation URL in responses.

5. **Temperature = 0 for all nodes** — Grading and structured output nodes require deterministic outputs. Temperature 0 ensures consistent grading decisions and valid JSON schema outputs.

---

## 15. Project Structure

```
RAG-Based Technical Documentation Assistant/
│
├── README.md                    ← This file
├── Dockerfile                   ← Production (port 7860 for HF Spaces)
├── docker-compose.yml           ← Local dev (port 8000)
├── requirements.txt
├── .env.example                 ← Environment variable template
├── feedback.jsonl               ← Appended feedback log
│
├── app/
│   ├── main.py                  ← FastAPI app, CORS, routes, static mount
│   ├── config.py                ← Pydantic Settings (reads .env)
│   │
│   ├── api/
│   │   ├── models.py            ← Request/response Pydantic schemas
│   │   └── routes/
│   │       ├── query.py         ← POST /query
│   │       ├── ingest.py        ← POST /ingest, POST /ingest/file
│   │       ├── documents.py     ← GET /documents
│   │       └── feedback.py      ← POST /feedback
│   │
│   ├── graph/
│   │   ├── state.py             ← RAGState TypedDict
│   │   ├── nodes.py             ← All 5 node functions
│   │   ├── edges.py             ← route_after_grading() router
│   │   └── workflow.py          ← Compiled StateGraph
│   │
│   ├── rag/
│   │   ├── embeddings.py        ← gemini-embedding-2 init
│   │   ├── vector_store.py      ← ChromaDB client + retriever
│   │   └── ingestion.py        ← URL + PDF ingestion pipelines
│   │
│   └── static/
│       ├── index.html           ← Chat interface
│       ├── style.css            ← Glassmorphism dark-mode design
│       └── app.js               ← Chat logic, BYOK, feedback, PDF upload
│
├── scripts/
│   └── ingest_docs.py           ← One-shot corpus ingestion script
│
└── docs/                        ← Detailed design documentation
    ├── architecture.md
    ├── api-spec.md
    ├── corpus-strategy.md
    └── design-decisions.md
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GEMINI_LLM_MODEL` | `models/gemini-3.1-flash-lite` | LLM for all inference nodes |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-2` | Embedding model |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB persistence path |
| `CHROMA_COLLECTION_NAME` | `technical_docs` | Collection name |
| `RETRIEVAL_TOP_K` | `2` | Chunks retrieved per query |
| `MAX_RETRY_ATTEMPTS` | `2` | Max query rewrites before fallback |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

---

<div align="center">

Built for the **Express Analytics AI/ML Engineer Intern** take-home assignment.

Stack: **Python 3.11 · LangGraph · FastAPI · ChromaDB · Google Gemini · Docker**

🚀 [Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/IDKwhatiscorrect/RAG-Based-Technical-Documentation-Assistant)

</div>
