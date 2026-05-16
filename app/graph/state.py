from typing import TypedDict, List, Dict, Any, Optional

class RAGState(TypedDict):
    """
    The state dictionary that flows between all nodes in the LangGraph workflow.
    """
    question: str                   # Original user question
    rewritten_query: str            # Query after analysis/rewrite
    query_type: str                 # conceptual | how-to | troubleshooting | api-ref
    retrieved_docs: List[Any]       # Raw chunk documents from ChromaDB
    graded_docs: List[Any]          # Filtered relevant chunk documents only
    generation: str                 # Final answer text
    citations: List[Dict[str, str]] # Source references: list of dicts with 'document', 'url', 'chunk_preview'
    retry_count: int                # Tracks retry attempts (max: 2)
    answer_found: bool              # Whether we found a valid answer
    session_id: Optional[str]       # Session identifier — reserved for conversation memory (future use)
