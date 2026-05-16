# Project Structure
# RAG-Based Technical Documentation Assistant

> This document provides a complete map of the repository structure.
> It explains where everything is located and how the different components
> interact with each other.

---

## High-Level Directory Map

```text
RAG-Based Technical Documentation Assistant/
├── app/                  # Main application code (FastAPI + LangGraph)
├── chroma_db/            # Persistent vector database storage
├── docs/                 # Project documentation (this folder)
├── docs_corpus/          # Downloaded source documents (Markdown/HTML)
├── scripts/              # Standalone utilities and scripts
├── .env                  # Local environment variables (gitignored)
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Local multi-container Docker setup
└── requirements.txt      # Python dependencies
```

---

## Detailed Breakdown

### `app/` (The Core Application)

The `app` directory contains the FastAPI server and the LangGraph workflow logic. It is structured by domain.

```text
app/
├── main.py               # Application Entrypoint
│                         # Initializes FastAPI, mounts routes, sets up CORS
│
├── config.py             # Configuration Management
│                         # Uses Pydantic BaseSettings to load and validate
│                         # environment variables from .env
│
├── api/                  # FastAPI Layer (REST Endpoints)
│   ├── models.py         # Pydantic schemas (Request/Response validation)
│   └── routes/           # Endpoint handlers
│       ├── query.py      # POST /query (invokes LangGraph)
│       ├── ingest.py     # POST /ingest (handles file/URL ingestion)
│       ├── documents.py  # GET /documents (queries ChromaDB)
│       └── feedback.py   # POST /feedback (saves user ratings)
│
├── graph/                # LangGraph Workflow Layer
│   ├── state.py          # Defines RAGState TypedDict
│   ├── nodes.py          # Core logic (Analyze, Retrieve, Grade, Generate)
│   ├── edges.py          # Routing logic (Conditional edges)
│   └── workflow.py       # Assembles nodes and edges into the StateGraph
│
├── rag/                  # RAG Utility Layer
│   ├── embeddings.py     # Wraps Gemini text-embedding-004
│   ├── vector_store.py   # ChromaDB client initialization and querying
│   └── ingestion.py      # Document loading, cleaning, and chunking logic
│
└── utils/                # General Utilities
    └── logger.py         # Loguru configuration for structured logging
```

### `chroma_db/` (Vector Storage)

This directory is automatically created and managed by ChromaDB. It contains the persistent SQLite database and vector index files. It is bound as a volume in `docker-compose.yml` so data survives container restarts.

### `docs_corpus/` (Source Documents)

A requirement of the assignment. This directory stores the raw downloaded text/HTML/Markdown of the documents that make up the knowledge base.

### `scripts/` (Utilities)

```text
scripts/
└── ingest_docs.py        # Standalone script to fetch URLs defined in
                          # corpus-strategy.md and populate ChromaDB.
                          # Run this once before starting the app.
```

---

## Execution Flow

When a user submits a question via the API, the execution traverses the application structure as follows:

1. **`app/main.py`** receives the HTTP request.
2. The request is routed to **`app/api/routes/query.py`**.
3. **`app/api/models.py`** validates the incoming JSON payload.
4. The route handler instantiates the LangGraph workflow defined in **`app/graph/workflow.py`**.
5. The workflow executes its nodes (**`app/graph/nodes.py`**), updating the state (**`app/graph/state.py`**).
6. The `Retrieve` node uses the vector store client from **`app/rag/vector_store.py`**.
7. The workflow completes, and the result is returned to the user through the FastAPI response model.
