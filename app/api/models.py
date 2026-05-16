from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional, Any

# --- /query Endpoints ---

class QueryRequest(BaseModel):
    question: str = Field(..., description="The technical question to ask the assistant")
    session_id: Optional[str] = Field(default=None, description="Optional session ID for tracking conversation history")

class Citation(BaseModel):
    document: str = Field(..., description="Source document name or URL")
    url: str = Field(..., description="Direct link to the source if available")
    chunk_preview: str = Field(..., description="A snippet of the text used to answer the question")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="The generated answer from the LLM")
    sources: List[Citation] = Field(..., description="List of sources used to generate the answer")
    query_type: str = Field(..., description="Classification of the query (e.g., how-to, conceptual)")
    retries_used: int = Field(..., description="Number of times the system had to rewrite the query to find relevant documents")
    session_id: Optional[str] = Field(default=None, description="The session ID associated with this query")


# --- /ingest Endpoints ---

class IngestURLRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., description="List of URLs to fetch and ingest")

class IngestResponse(BaseModel):
    status: str = Field(..., description="Success or failure status")
    documents_ingested: int = Field(..., description="Number of unique documents processed")
    chunks_created: int = Field(..., description="Number of vector chunks created and stored")
    collection: str = Field(..., description="The ChromaDB collection name used")
    message: str = Field(..., description="Detailed result message")


# --- /documents Endpoints ---

class DocumentChunk(BaseModel):
    id: str = Field(..., description="Unique ID of the chunk in ChromaDB")
    content_preview: str = Field(..., description="First 100 characters of the chunk")
    metadata: Dict[str, Any] = Field(..., description="Associated metadata (source URL, etc.)")

class DocumentsResponse(BaseModel):
    total_chunks: int = Field(..., description="Total number of chunks in the database")
    chunks: List[DocumentChunk] = Field(..., description="List of document chunks (paginated)")


# --- /feedback Endpoints ---

class FeedbackRequest(BaseModel):
    query_id: str = Field(..., description="ID of the query being rated")
    rating: str = Field(..., description="'up' or 'down'")
    comment: Optional[str] = Field(default=None, description="Optional text comment explaining the rating")

class FeedbackResponse(BaseModel):
    status: str = Field(..., description="Status of the feedback submission")
    message: str = Field(..., description="Confirmation message")
