# API Specification
# RAG-Based Technical Documentation Assistant

> **Base URL (local):** `http://localhost:8000`
> **Base URL (HF Spaces):** `https://<your-hf-space>.hf.space`
> **Framework:** FastAPI (auto-generates interactive docs at `/docs`)
> **Auth:** None (open API for this assignment)

---

## Endpoints Overview

| Method | Endpoint     | Purpose                        |
|--------|-------------|--------------------------------|
| `POST` | `/query`     | Submit a question, get answer  |
| `POST` | `/ingest`    | Ingest new documents           |
| `GET`  | `/documents` | List all indexed documents     |
| `POST` | `/feedback`  | Submit feedback on an answer   |
| `GET`  | `/health`    | Health check (used by Docker)  |

---

## 1. POST `/query`

Submit a natural language question. The system runs the full LangGraph
RAG pipeline and returns an answer grounded in the indexed documents.

### Request Body

```json
{
  "question": "How do I add memory to a LangGraph agent?",
  "session_id": "user-session-abc123"
}
```

| Field        | Type     | Required | Description                                              |
|--------------|----------|----------|----------------------------------------------------------|
| `question`   | `string` | ✅ Yes   | The natural language question to answer                  |
| `session_id` | `string` | ❌ No    | Optional session ID for future conversation memory support |

### Response — 200 OK

```json
{
  "answer": "To add memory to a LangGraph agent, you use a checkpointer...",
  "sources": [
    {
      "document": "LangGraph Documentation",
      "url": "https://langchain-ai.github.io/langgraph/concepts/memory/",
      "chunk_preview": "LangGraph supports persistent memory via checkpointers..."
    },
    {
      "document": "LangChain Documentation",
      "url": "https://docs.langchain.com/docs/",
      "chunk_preview": "Memory in LangChain agents can be implemented using..."
    }
  ],
  "query_type": "how-to",
  "rewritten_query": "LangGraph agent memory checkpointer persistent state",
  "retry_count": 0,
  "answer_found": true,
  "session_id": "user-session-abc123"
}
```

| Field            | Type      | Description                                              |
|------------------|-----------|----------------------------------------------------------|
| `answer`         | `string`  | The generated answer grounded in retrieved documents     |
| `sources`        | `array`   | List of source documents used to generate the answer     |
| `query_type`     | `string`  | Classified query type: `conceptual`, `how-to`, `troubleshooting`, `api-reference` |
| `rewritten_query`| `string`  | The expanded/rewritten query used for retrieval          |
| `retry_count`    | `integer` | Number of retrieval retries performed (0, 1, or 2)       |
| `answer_found`   | `boolean` | Whether relevant documents were found                    |
| `session_id`     | `string`  | Echoed back from the request                             |

### Response — 200 OK (No relevant docs found)

```json
{
  "answer": "I don't have enough information in my knowledge base to answer this question accurately. Please try rephrasing or ask about LangChain, LangGraph, or FastAPI.",
  "sources": [],
  "query_type": "unknown",
  "rewritten_query": "...",
  "retry_count": 2,
  "answer_found": false,
  "session_id": "user-session-abc123"
}
```

### Error Responses

| Status | Reason                        | Response Body                                      |
|--------|-------------------------------|----------------------------------------------------|
| `422`  | Missing/invalid `question`    | `{ "detail": "field required: question" }`         |
| `500`  | LLM or ChromaDB failure       | `{ "detail": "Internal pipeline error: ..." }`     |

### curl Example

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is a StateGraph in LangGraph?",
    "session_id": "test-session-001"
  }'
```

---

## 2. POST `/ingest`

Ingest new documents into the ChromaDB vector store. Accepts either a
file upload or a list of URLs to fetch and index.

### Request — File Upload (multipart/form-data)

```bash
curl -X POST "http://localhost:8000/ingest" \
  -F "files=@/path/to/document.pdf" \
  -F "files=@/path/to/readme.md"
```

| Field   | Type   | Required | Description                          |
|---------|--------|----------|--------------------------------------|
| `files` | `file` | ✅ Yes   | One or more files (PDF, MD, TXT, HTML)|

### Request — URL Ingestion (application/json)

```json
{
  "urls": [
    "https://langchain-ai.github.io/langgraph/concepts/",
    "https://fastapi.tiangolo.com/tutorial/"
  ],
  "collection_name": "technical_docs"
}
```

| Field             | Type           | Required | Description                             |
|-------------------|----------------|----------|-----------------------------------------|
| `urls`            | `list[string]` | ✅ Yes   | List of URLs to fetch and index         |
| `collection_name` | `string`       | ❌ No    | ChromaDB collection to use (default: `technical_docs`) |

### Response — 200 OK

```json
{
  "status": "success",
  "documents_ingested": 3,
  "chunks_created": 147,
  "collection": "technical_docs",
  "message": "3 documents ingested and indexed successfully."
}
```

| Field                 | Type      | Description                                    |
|-----------------------|-----------|------------------------------------------------|
| `status`              | `string`  | `success` or `partial` (if some docs failed)  |
| `documents_ingested`  | `integer` | Number of source documents processed           |
| `chunks_created`      | `integer` | Total number of chunks stored in ChromaDB      |
| `collection`          | `string`  | ChromaDB collection name used                  |
| `message`             | `string`  | Human-readable summary                         |

### Error Responses

| Status | Reason                        | Response Body                                       |
|--------|-------------------------------|-----------------------------------------------------|
| `400`  | Unsupported file type         | `{ "detail": "File type .xyz not supported" }`      |
| `422`  | No files or URLs provided     | `{ "detail": "Provide at least one file or URL" }`  |
| `500`  | Embedding or storage failure  | `{ "detail": "Ingestion failed: ..." }`             |

---

## 3. GET `/documents`

List all documents currently indexed in the ChromaDB vector store.
Useful for debugging and understanding what's in the corpus.

### Request

No body required. Optional query parameters:

| Parameter    | Type      | Default | Description                              |
|--------------|-----------|---------|------------------------------------------|
| `collection` | `string`  | `technical_docs` | ChromaDB collection to query  |
| `limit`      | `integer` | `50`    | Max number of documents to return        |

### curl Example

```bash
curl "http://localhost:8000/documents?limit=10"
```

### Response — 200 OK

```json
{
  "total_chunks": 147,
  "total_documents": 3,
  "collection": "technical_docs",
  "documents": [
    {
      "id": "chunk-001",
      "source": "LangGraph Documentation",
      "url": "https://langchain-ai.github.io/langgraph/concepts/",
      "chunk_index": 0,
      "preview": "LangGraph is a library for building stateful, multi-actor applications..."
    },
    {
      "id": "chunk-002",
      "source": "LangGraph Documentation",
      "url": "https://langchain-ai.github.io/langgraph/concepts/",
      "chunk_index": 1,
      "preview": "A StateGraph is the core abstraction in LangGraph..."
    }
  ]
}
```

| Field             | Type      | Description                                        |
|-------------------|-----------|----------------------------------------------------|
| `total_chunks`    | `integer` | Total number of chunks stored in ChromaDB          |
| `total_documents` | `integer` | Number of unique source documents                  |
| `collection`      | `string`  | ChromaDB collection queried                        |
| `documents`       | `array`   | List of chunk metadata (id, source, url, preview)  |

### Error Responses

| Status | Reason                     | Response Body                                         |
|--------|----------------------------|-------------------------------------------------------|
| `404`  | Collection does not exist  | `{ "detail": "Collection 'xyz' not found" }`          |
| `500`  | ChromaDB connection error  | `{ "detail": "Vector store unavailable: ..." }`       |

---

## 4. POST `/feedback`

Submit user feedback on a generated answer. Supports thumbs up/down
and an optional comment. Stored locally for future analysis.

### Request Body

```json
{
  "question": "What is a StateGraph in LangGraph?",
  "answer": "A StateGraph is the core abstraction...",
  "rating": "up",
  "comment": "Great answer, very clear!",
  "session_id": "user-session-abc123"
}
```

| Field        | Type     | Required | Description                                              |
|--------------|----------|----------|----------------------------------------------------------|
| `question`   | `string` | ✅ Yes   | The original question asked                              |
| `answer`     | `string` | ✅ Yes   | The answer that was generated                            |
| `rating`     | `string` | ✅ Yes   | `"up"` (helpful) or `"down"` (not helpful)               |
| `comment`    | `string` | ❌ No    | Optional free-text comment from the user                 |
| `session_id` | `string` | ❌ No    | Session identifier for tracking                          |

### Response — 201 Created

```json
{
  "status": "received",
  "feedback_id": "fb-20250515-001",
  "message": "Thank you for your feedback!"
}
```

### Error Responses

| Status | Reason                        | Response Body                                           |
|--------|-------------------------------|---------------------------------------------------------|
| `422`  | Invalid `rating` value        | `{ "detail": "rating must be 'up' or 'down'" }`        |
| `422`  | Missing required fields       | `{ "detail": "field required: question" }`              |

### curl Example

```bash
curl -X POST "http://localhost:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is a StateGraph in LangGraph?",
    "answer": "A StateGraph is the core abstraction...",
    "rating": "up",
    "comment": "Very helpful!",
    "session_id": "test-session-001"
  }'
```

---

## 5. GET `/health`

Health check endpoint. Used by Docker's `healthcheck` directive and
monitoring tools to verify the application is running.

### Response — 200 OK

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_store": "connected",
  "llm": "gemini-1.5-flash"
}
```

### curl Example

```bash
curl "http://localhost:8000/health"
```

---

## Pydantic Models Reference

All request and response bodies are validated using Pydantic models
defined in `app/api/models.py`.

```python
# Request Models
class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class IngestURLRequest(BaseModel):
    urls: list[str]
    collection_name: str = "technical_docs"

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: Literal["up", "down"]
    comment: Optional[str] = None
    session_id: Optional[str] = None

# Response Models
class SourceDocument(BaseModel):
    document: str
    url: str
    chunk_preview: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceDocument]
    query_type: str
    rewritten_query: str
    retry_count: int
    answer_found: bool
    session_id: Optional[str] = None

class IngestResponse(BaseModel):
    status: str
    documents_ingested: int
    chunks_created: int
    collection: str
    message: str

class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str
    message: str
```

---

## Interactive API Docs

FastAPI automatically generates two interactive documentation UIs:

| UI | URL | Description |
|----|-----|-------------|
| **Swagger UI** | `http://localhost:8000/docs` | Interactive — try endpoints directly in browser |
| **ReDoc** | `http://localhost:8000/redoc` | Clean read-only API reference |

---

*This spec is the contract between the API layer (`app/api/`) and any client.
All Pydantic models in `app/api/models.py` must match these schemas exactly.*
