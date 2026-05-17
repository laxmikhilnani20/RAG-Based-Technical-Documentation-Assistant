# RAG-Based Technical Documentation Assistant
**Express Analytics — AI/ML Engineer Intern Assignment Submission**

---

| | |
|---|---|
| **Submitted by** | Laxmi Khilnani |
| **Role** | AI/ML Engineer Intern |
| **Live Demo** | https://huggingface.co/spaces/IDKwhatiscorrect/RAG-Based-Technical-Documentation-Assistant |
| **GitHub** | https://github.com/laxmikhilnani20/RAG-Based-Technical-Documentation-Assistant |
| **Stack** | Python 3.11 · LangGraph · FastAPI · ChromaDB · Google Gemini · Docker |

---

## What Was Built

A **production-grade, self-corrective RAG (Retrieval-Augmented Generation) system** that answers technical questions about LangGraph, LangChain, and FastAPI using real, indexed documentation as its knowledge base.

The system does **not** rely on the LLM's training data. Every answer is grounded in retrieved documentation chunks, with citations pointing to the exact source. If retrieval fails, the system automatically rewrites the query and retries — up to 2 times — before gracefully falling back.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│               Browser (Chat UI)                     │
│  Dark glassmorphism interface · Markdown rendering  │
│  API key input (BYOK) · PDF upload · Feedback       │
└──────────────────────┬──────────────────────────────┘
                       │  POST /query  (x-api-key header)
                       ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Application                    │
│  /query · /ingest · /ingest/file                    │
│  /documents · /feedback · /health                   │
│  Serves the chat UI at GET /                        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          LangGraph Self-Corrective Pipeline         │
│                                                     │
│  [1] analyze_query                                  │
│       └─ Rewrites question for vector search        │
│       └─ Classifies query type                      │
│                  │                                  │
│  [2] retrieve_docs                                  │
│       └─ Embeds query · Searches ChromaDB (top-2)   │
│                  │                                  │
│  [3] grade_documents                                │
│       └─ LLM grades each chunk: relevant / not      │
│       └─ Filters out irrelevant chunks              │
│                  │                                  │
│      ┌───────────┴───────────────┐                  │
│      │    Conditional Router     │                  │
│      └───┬───────────────────┬───┘                  │
│     docs found           no docs found              │
│          │               retry_count < 2            │
│          │                    │                     │
│  [4] generate_answer    [5] rewrite_query           │
│       └─ Grounded answer      └─ New phrasing       │
│       └─ Citations            └─ → retrieve again   │
│       └─ Fallback if                                │
│          retries exhausted                          │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   ChromaDB (Vector Store)    Google Gemini API
   Persistent · Local          LLM: gemini-3.1-flash-lite
   Collection: technical_docs  Embeddings: gemini-embedding-2
   Chunk size: 1000 chars       Temperature: 0 (deterministic)
   Top-K retrieval: 2
```

---

## The Self-Corrective Loop — What Makes This Agentic

Most RAG systems are a **one-shot pipeline**: retrieve → generate. This system uses LangGraph to implement a **cyclical, self-corrective loop**:

1. After retrieving documents, an LLM **grades each chunk** for relevance (yes/no)
2. If **no relevant chunks** are found, the system **rewrites the query** with different phrasing and tries again
3. This retry loop runs a **maximum of 2 times** (tracked in `RAGState.retry_count`)
4. After exhausting retries, the system emits a **graceful fallback** — it never hallucinates

This pattern is inspired by CRAG (Corrective RAG) and makes the system significantly more robust than a naive retriever.

---

## All Assignment Requirements — Fulfilled

### LangGraph Workflow

| Node | Implementation | File |
|---|---|---|
| Node 1: Query Analysis | `analyze_query()` — rewrites query + classifies type using structured LLM output | `app/graph/nodes.py` |
| Node 2: Retrieval | `retrieve_docs()` — embeds query, searches ChromaDB top-K=2 | `app/graph/nodes.py` |
| Node 3: Document Grading | `grade_documents()` — LLM grades each chunk yes/no, filters irrelevant | `app/graph/nodes.py` |
| Node 4: Generation | `generate_answer()` — grounded answer with citations, fallback if no docs | `app/graph/nodes.py` |
| Conditional Edge | `route_after_grading()` — routes to generate / rewrite / fallback | `app/graph/edges.py` |
| Retry Loop | `rewrite_query()` → back to `retrieve_docs`, max 2 retries | `app/graph/nodes.py` |

### Ingestion Pipeline

| Step | Implementation |
|---|---|
| Load from URLs | `WebBaseLoader` — fetches official documentation pages |
| Load from PDFs | `PyPDFLoader` — handles local PDF files |
| Chunk documents | `RecursiveCharacterTextSplitter` — 1000 chars, 200 overlap |
| Generate embeddings | `GoogleGenerativeAIEmbeddings` — `gemini-embedding-2` |
| Store in ChromaDB | `Chroma` with `PersistentClient` — data survives restarts |
| Deterministic IDs | `MD5(source_url + chunk_index)` — enables safe re-ingestion (upserts) |

### API Endpoints

| Method | Endpoint | Status | Purpose |
|---|---|:---:|---|
| `POST` | `/query` | ✅ | Submit question → returns answer + citations |
| `POST` | `/ingest` | ✅ | Ingest URLs into ChromaDB |
| `POST` | `/ingest/file` | ✅ | Upload & ingest PDF |
| `GET` | `/documents` | ✅ | List all indexed chunks |
| `POST` | `/feedback` | ✅ | Submit thumbs up/down rating |
| `GET` | `/health` | ✅ | Health check for Docker/HF Spaces |

### Bonus Features

| Bonus | Status | Notes |
|---|:---:|---|
| Simple UI | ✅ **Exceeded** | Full glassmorphism production UI — beyond Streamlit/Gradio |
| PDF upload via UI | ✅ | Sidebar PDF ingestion panel |
| Session ID support | ✅ | `session_id` in state — foundation for conversation memory |
| Hallucination check | ❌ | Would add as a 5th LangGraph node |
| Web search fallback | ❌ | Would integrate Tavily as a 6th node |

---

## Document Corpus

The default knowledge base covers **4 official documentation pages**:

| Document | Source URL |
|---|---|
| LangGraph — Low Level Concepts | `langchain-ai.github.io/langgraph/concepts/low_level/` |
| LangGraph — High Level Concepts | `langchain-ai.github.io/langgraph/concepts/high_level/` |
| LangChain — RAG Concepts | `python.langchain.com/docs/concepts/rag/` |
| FastAPI — First Steps | `fastapi.tiangolo.com/tutorial/first-steps/` |

Documents are ingested via `scripts/ingest_docs.py`. Users can also add their own documents at runtime via `POST /ingest` (URL) or `POST /ingest/file` (PDF upload through the UI).

---

## Key Design Decisions

### 1 — Why LangGraph instead of a simple chain?

A standard `LangChain` chain is **linear** — it can't loop back. LangGraph's `StateGraph` enables **cyclical, conditional routing**, which is the only way to implement the retry loop (grade → rewrite → retrieve → grade again). Without LangGraph, the system would be a naive one-shot RAG with no self-correction capability.

### 2 — Why ChromaDB?

ChromaDB runs **fully in-process** with disk persistence (`PersistentClient`). No separate database server is needed — the entire vector store is a folder on disk. This makes it ideal for containerized deployment where spinning up a separate vector DB server adds unnecessary complexity.

### 3 — BYOK (Bring Your Own Key) Architecture

The Gemini free tier has a 15 RPM limit. If a single server-side key were used, sharing it across all users would exhaust it instantly. With BYOK, each user's quota is independent. The API key is passed via the `x-api-key` request header, flows through `RAGState.api_key`, and is used directly with the Gemini SDK — **it is never logged, stored, or persisted**.

### 4 — Structured Outputs for Grading

Both the grader and query analyzer use `llm.with_structured_output(PydanticModel)`. This **guarantees valid JSON schema output** from the LLM, eliminating fragile string parsing. The grader always returns `{"is_relevant": "yes"}` or `{"is_relevant": "no"}` — never an ambiguous free-form response.

### 5 — Deterministic Chunk IDs

```python
chunk_id = MD5(source_url + chunk_index)
```

Re-ingesting the same URL **upserts** existing chunks rather than creating duplicates. The pipeline is idempotent — safe to run repeatedly.

---

## Chunking & Embedding Strategy

**Chunker:** `RecursiveCharacterTextSplitter` — chunk size `1000` chars, overlap `200` chars

This splitter tries to break at natural boundaries (`\n\n` paragraph → `\n` line → ` ` word) before falling back to character splits. This preserves sentence integrity far better than a naive fixed-character splitter.

- **1000 chars** (~200–250 tokens) is large enough to capture a complete technical concept, but small enough to remain semantically focused for retrieval
- **200-char overlap** ensures sentences that straddle a chunk boundary are captured in both adjacent chunks — no information falls into a gap

**Embedding model:** `models/gemini-embedding-2`

Google's state-of-the-art semantic embedding model. Chosen over sentence-transformers because it integrates natively with the rest of the Gemini API (single provider, single key), produces high-dimensional vectors optimized for semantic similarity, and works within the free tier.

---

## How to Run

### Option A — Local (Python)

```bash
# Clone and install
git clone https://github.com/laxmikhilnani20/RAG-Based-Technical-Documentation-Assistant.git
cd "RAG-Based Technical Documentation Assistant"
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Ingest the corpus (one-time setup — requires a Gemini API key)
GEMINI_API_KEY=your_key python scripts/ingest_docs.py

# Start the server
uvicorn app.main:app --reload --port 8000
# → Open http://localhost:8000
```

### Option B — Docker

```bash
docker compose up --build
# → Open http://localhost:8000
```

### Option C — Live Demo (No setup required)

> **https://huggingface.co/spaces/IDKwhatiscorrect/RAG-Based-Technical-Documentation-Assistant**

1. Open the link
2. Paste your Gemini API key in the sidebar (get one free at [aistudio.google.com](https://aistudio.google.com/app/apikey))
3. Ask a question about LangGraph, LangChain, or FastAPI

---

## Example API Request & Response

**Request:**
```http
POST /query
Content-Type: application/json
x-api-key: AIzaSy...

{ "question": "How do I add a node to a LangGraph StateGraph?" }
```

**Response:**
```json
{
  "answer": "To add a node to a LangGraph StateGraph, you use the `add_node()` method...",
  "sources": [
    {
      "document": "https://langchain-ai.github.io/langgraph/concepts/low_level/",
      "url": "https://langchain-ai.github.io/langgraph/concepts/low_level/",
      "chunk_preview": "Nodes are added to the graph using workflow.add_node(name, function)..."
    }
  ],
  "query_type": "how-to",
  "retries_used": 0,
  "session_id": "3f2a1b..."
}
```

---

## What I Would Improve With More Time

1. **Hallucination check node** — A 5th LangGraph node that verifies the generated answer is supported by the retrieved context (Self-RAG pattern). Currently the system relies on the LLM's instruction-following to stay grounded.

2. **Web search fallback** — A 6th node using Tavily that kicks in when the vector store has no relevant results after all retries, before emitting the "I don't know" fallback.

3. **Full conversation memory** — Wire `session_id` into a Redis or in-memory store to maintain chat history across turns, enabling natural follow-up questions.

4. **Streaming responses** — Use FastAPI `StreamingResponse` to show tokens in real-time rather than waiting for the full generation.

5. **RAGAS evaluation** — Automated evaluation of faithfulness, answer relevancy, and context precision to measure RAG quality objectively.

---

## Project Structure (Summary)

```
app/
├── main.py              ← FastAPI app
├── config.py            ← Environment settings
├── api/routes/          ← /query /ingest /documents /feedback
├── graph/               ← LangGraph nodes, edges, state, workflow
├── rag/                 ← ChromaDB, embeddings, ingestion
└── static/              ← Chat UI (HTML + CSS + JS)

scripts/
└── ingest_docs.py       ← One-shot corpus ingestion

Dockerfile               ← Production (port 7860 for HF Spaces)
docker-compose.yml       ← Local dev (port 8000)
requirements.txt
README.md                ← Full technical documentation
```

---

## Author

**Laxmi Khilnani**

| | |
|---|---|
| 🌐 Portfolio | [laxmikhilnani20.github.io/Resume](https://laxmikhilnani20.github.io/Resume/) |
| 💼 LinkedIn | [linkedin.com/in/laxmi-khilnani20](https://www.linkedin.com/in/laxmi-khilnani20/) |
| 🐙 GitHub | [github.com/laxmikhilnani20](https://github.com/laxmikhilnani20) |

---

*Thank you for reviewing this submission. The full README.md in the repository contains deeper documentation of every component, all API endpoints with examples, and the complete project structure.*
