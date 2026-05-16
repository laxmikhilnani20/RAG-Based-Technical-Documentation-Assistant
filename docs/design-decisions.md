# Design Decisions & Tradeoffs
# RAG-Based Technical Documentation Assistant

> The Express Analytics assignment evaluates clear thinking and honest
> documentation of tradeoffs over feature completeness. This document
> outlines the reasoning behind major architectural choices.

---

## 1. Why LangGraph over plain LangChain?

While standard LangChain (LCEL) is excellent for linear pipelines, it struggles
with cyclical or self-corrective logic.

**The Problem:** The assignment requires *self-corrective* document grading. If
retrieved documents are irrelevant, the system must loop back, rewrite the query,
and retrieve again.

**The Solution:** LangGraph models this as a state machine (`StateGraph`).
- **Nodes** perform atomic tasks (Retrieve, Grade, Generate).
- **Conditional Edges** handle the routing (`if all_irrelevant -> loop back to Retrieve`).
- **State** (`RAGState`) tracks the `retry_count` cleanly, preventing infinite loops.

**Tradeoff:** LangGraph adds a steeper learning curve and slightly more boilerplate
than a simple linear chain. However, for agentic, multi-step reasoning, it is
the industry standard and directly aligns with the assignment's core goal.

---

## 2. Why Gemini 1.5 Flash?

The pipeline requires two models: an LLM for reasoning/generation, and an
embedding model for retrieval.

| Option | Pros | Cons |
|--------|------|------|
| OpenAI (GPT-4o-mini) | Industry standard, cheap | Requires billing setup, separate key |
| Groq (Llama 3) | Extremely fast inference | No native embedding model |
| **Google Gemini Flash** | **Fast, generous free tier, handles BOTH** | Slightly less context window than Pro |

**Decision:** We chose Gemini because a single API key provides access to both
a high-quality LLM (`gemini-1.5-flash`) and a state-of-the-art embedding model
(`text-embedding-004`). This drastically reduces configuration complexity for
reviewers evaluating the project.

---

## 3. Why ChromaDB over FAISS?

Both were suggested in the assignment prompt.

| Feature | ChromaDB | FAISS |
|---------|----------|-------|
| Setup | `pip install chromadb` | C++ bindings required |
| Persistence | ✅ Native (saves to disk) | ❌ Manual serialization needed |
| Metadata filtering | ✅ Native | ❌ Complex to implement |

**Decision:** We chose ChromaDB. The assignment requires a `GET /documents`
endpoint to list indexed documents. ChromaDB's native metadata filtering and
persistence make querying the existing corpus trivial. FAISS is faster at massive
scale (millions of vectors), but for a 3–5 document corpus, ChromaDB's developer
experience wins.

---

## 4. Why FastAPI + Docker + Hugging Face Spaces?

The assignment requires a "working FastAPI application that can be run locally."

**The typical approach:** Just provide a `main.py` and tell the reviewer to run
`uvicorn`.

**Our approach:** We wrapped the FastAPI app in Docker and targeted deployment
on Hugging Face Spaces.
- **Why?** Reviewers hate installing dependencies and debugging environment issues.
  By providing a Dockerized solution, we guarantee it runs anywhere.
- **Tradeoff:** Docker adds overhead to the development process. We mitigated this
  by creating a `docker-compose.yml` for local testing that mirrors the HF Spaces
  environment.

---

## 5. The "Query Rewriting" Strategy

In Node 1, we don't just pass the user's raw question to the retriever. We use
the LLM to rewrite it.

**Why?** Users often ask terse, ambiguous questions (e.g., "how do I use memory?").
Vector search (cosine similarity) relies on keyword/semantic overlap.
- *Raw Query:* "how do I use memory?"
- *Rewritten Query:* "LangGraph StateGraph memory implementation checkpointer persistent state examples"

The rewritten query contains dense domain-specific terminology, drastically
improving retrieval accuracy from technical documentation.

---

## 6. What we would improve with more time

If this were a production system with more than 2 days allocated, we would add:

1. **Hallucination Checker (Self-RAG):** An additional LangGraph node *after*
   generation that grades whether the generated answer is actually supported by
   the retrieved context, preventing confident fabrication.
2. **Conversation Memory (Session State):** We added `session_id` to the state
   schema, but haven't implemented the backing store (e.g., Redis or SQLite) to
   fetch previous turns. This would allow follow-up questions ("what about the
   other method?").
3. **Web Search Fallback (Tavily):** If the vector store fails after 2 retries,
   routing the query to a web search API before returning an error. We removed
   this to focus on the core vector-based RAG pipeline first.
4. **Async Execution:** Converting the LangGraph nodes to use `ainvoke` and
   async HTTP clients for better throughput under concurrent load.
