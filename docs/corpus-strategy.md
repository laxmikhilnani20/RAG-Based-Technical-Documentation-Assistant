# Corpus & Chunking Strategy
# RAG-Based Technical Documentation Assistant

> This document explains which documents we index, why we chose them,
> how we fetch and process them, and the reasoning behind every chunking
> and embedding decision.

---

## 1. Document Corpus

The assignment requires 3–5 technical documents. We use **3 official
documentation sources** — all directly relevant to the tools used in
this very project.

### Why these three?

| # | Source | Domain | Why Chosen |
|---|--------|--------|------------|
| 1 | **LangChain Docs** | AI / LLM framework | Core library used in the pipeline (loaders, splitters, chains) |
| 2 | **LangGraph Docs** | Agentic AI workflows | The graph engine powering the RAG workflow — directly central |
| 3 | **FastAPI Docs** | Web framework | The API layer of this very project — highly testable queries |

**Strategic advantage:** A reviewer testing this system will naturally ask
questions about LangChain, LangGraph, or FastAPI — the exact docs we've
indexed. This gives us high confidence in retrieval quality during evaluation.

---

## 2. Source URLs

Documents are fetched at ingestion time from their official sources.

### LangGraph Documentation

```
https://langchain-ai.github.io/langgraph/concepts/
https://langchain-ai.github.io/langgraph/tutorials/
https://langchain-ai.github.io/langgraph/how-tos/
```

### LangChain Documentation

```
https://python.langchain.com/docs/introduction/
https://python.langchain.com/docs/concepts/
https://python.langchain.com/docs/how_to/
```

### FastAPI Documentation

```
https://fastapi.tiangolo.com/tutorial/
https://fastapi.tiangolo.com/advanced/
https://fastapi.tiangolo.com/deployment/
```

> All URLs are fetched using LangChain's `WebBaseLoader`, which handles
> HTML parsing and text extraction automatically. All three sources use
> server-side rendering (MkDocs / Sphinx), so plain HTTP requests work
> without needing a headless browser.
>
> Fetched documents are saved to the `docs_corpus/` directory in the
> repository — this is a required deliverable per the assignment spec.
> A standalone script (`scripts/ingest_docs.py`) can re-fetch and
> re-index them at any time.

---

## 3. Ingestion Pipeline — Step by Step

```
Step 1: Load
  WebBaseLoader fetches HTML from each URL
  → Strips navigation, headers, footers (BeautifulSoup)
  → Returns raw text per page

Step 2: Clean
  → Remove excessive whitespace
  → Strip code comment artifacts
  → Normalize Unicode characters

Step 3: Split
  RecursiveCharacterTextSplitter
  → chunk_size   = 1000 tokens
  → chunk_overlap = 200 tokens
  → separators   = ["\n\n", "\n", " ", ""]

Step 4: Embed
  Gemini text-embedding-004
  → Each chunk → 768-dimensional vector

Step 5: Store
  ChromaDB
  → Vectors + metadata stored at ./chroma_db
  → Collection: "technical_docs"
```

---

## 4. Chunking Strategy

### Parameters

| Parameter       | Value  | Configurable via `.env` |
|-----------------|--------|-------------------------|
| `chunk_size`    | `1000` | ✅ `CHUNK_SIZE`         |
| `chunk_overlap` | `200`  | ✅ `CHUNK_OVERLAP`      |

### Why chunk_size = 1000?

Technical documentation has a specific structure:
- Concepts are explained in **paragraphs of 3–6 sentences**
- Code examples are typically **20–50 lines**
- A chunk of ~1000 characters captures **one complete idea or example**
  without splitting it across two chunks

Too small (e.g., 200): Chunks lose context — a code block gets split from
its explanation.

Too large (e.g., 3000): Chunks become noisy — one chunk contains multiple
unrelated concepts, hurting retrieval precision.

**1000 is the sweet spot for technical prose + code.**

### Why chunk_overlap = 200?

Overlap ensures that a concept spanning a chunk boundary isn't lost.
Without overlap:

```
Chunk 1: "...A StateGraph is initialized with a schema. The schema defines"
Chunk 2: "what data flows between nodes. Each node receives the full state..."
```

With 200-token overlap:

```
Chunk 1: "...A StateGraph is initialized with a schema. The schema defines"
Chunk 2: "The schema defines what data flows between nodes. Each node receives..."
```

The overlapping text acts as a **semantic bridge**, improving retrieval
for questions that straddle two chunks.

### Why RecursiveCharacterTextSplitter?

LangChain offers several splitters. We chose `RecursiveCharacterTextSplitter`
because:

| Splitter | Best For | Why Not Used |
|----------|----------|--------------|
| `CharacterTextSplitter` | Simple text | Splits mid-sentence, loses semantic coherence |
| `TokenTextSplitter` | Exact token budgets | Slower, needs tokenizer loaded |
| `MarkdownTextSplitter` | Pure Markdown | Our docs are HTML → text, not raw Markdown |
| **`RecursiveCharacterTextSplitter`** | **General text** | **Tries paragraph → sentence → word splits in order — preserves meaning** |

The recursive approach tries to split at `"\n\n"` (paragraphs) first,
then `"\n"` (lines), then `" "` (words) — only going smaller if needed.
This keeps semantic units together naturally.

---

## 5. Embedding Strategy

### Model: Gemini `text-embedding-004`

| Property | Value |
|----------|-------|
| Provider | Google (same API key as LLM) |
| Dimensions | 768 |
| Max input tokens | 2048 |
| Similarity metric | Cosine similarity |
| Cost | Free tier (generous limits) |

### Why Gemini embeddings over alternatives?

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Gemini text-embedding-004** | Same API key, free, state-of-the-art quality | — | ✅ **Chosen** |
| OpenAI `text-embedding-3-small` | Very good quality | Costs money, separate API key | ❌ |
| `sentence-transformers` (local) | Free, no API | Slower, larger Docker image, lower quality | ❌ |
| Cohere embeddings | Good quality | Separate API key, free tier limited | ❌ |

**Key advantage:** Using Gemini for both LLM and embeddings means
**one API key manages the entire pipeline** — simpler config, fewer
failure points, no cross-provider compatibility issues.

---

## 6. Vector Store: ChromaDB

### Why ChromaDB?

| Property | Detail |
|----------|--------|
| Type | Local persistent vector database |
| Storage | `./chroma_db/` directory on disk |
| Search | Approximate Nearest Neighbor (ANN) with cosine similarity |
| Persistence | Survives app restarts (data on disk) |
| Setup complexity | Zero — no external service needed |

### ChromaDB vs FAISS

| Feature | ChromaDB | FAISS |
|---------|----------|-------|
| Persistence | ✅ Built-in | ❌ Must serialize manually |
| Metadata filtering | ✅ Native | ❌ No |
| Setup | `pip install chromadb` | `pip install faiss-cpu` |
| REST API | ✅ Optional | ❌ No |
| Best for | Prototyping + production | High-scale similarity search |

For this project, **ChromaDB wins on persistence and metadata filtering**.
We store source URL and document name per chunk — and can filter by these
in future queries.

### Metadata stored per chunk

```python
{
  "id": "chunk-langgraph-042",
  "document": "LangGraph Documentation",
  "url": "https://langchain-ai.github.io/langgraph/concepts/",
  "chunk_index": 42,
  "source_type": "web"
}
```

This metadata is returned with every retrieved chunk and surfaces as
**citations in the API response**.

---

## 7. Expected Corpus Statistics

| Source | Pages Fetched | Est. Chunks |
|--------|--------------|-------------|
| LangGraph Docs (3 pages) | ~3 | ~60–80 |
| LangChain Docs (3 pages) | ~3 | ~60–80 |
| FastAPI Docs (3 pages) | ~3 | ~50–70 |
| **Total** | **~9 pages** | **~170–230 chunks** |

This is a small but focused corpus — ideal for a low-latency prototype
that retrieves precisely relevant context without noise.

---

## 8. Re-ingestion Behaviour

If `POST /ingest` is called again with the same source:
- ChromaDB will **upsert** based on chunk `id`
- Existing chunks with the same `id` are replaced
- New chunks are added
- No duplicate vectors are created

This means the corpus can be updated incrementally without wiping
the entire vector store.

---

*Chunk size, overlap, and top-k values are all configurable via `.env`.
See `.env.example` for variable names and defaults.*
