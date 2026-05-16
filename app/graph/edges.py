import logging
from typing import Literal
from app.config import settings
from app.graph.state import RAGState

logger = logging.getLogger(__name__)

def route_after_grading(state: RAGState) -> Literal["generate_answer", "rewrite_query", "fallback_answer"]:
    """
    Determines the next node to execute based on the document grading results and retry count.
    """
    graded_docs = state.get("graded_docs", [])
    retry_count = state.get("retry_count", 0)
    
    # If we have at least one relevant document, proceed to generation
    if len(graded_docs) > 0:
        logger.info(f"ROUTING: Found {len(graded_docs)} relevant docs. Routing to generate_answer.")
        return "generate_answer"
        
    # If no relevant docs, check if we can retry
    if retry_count < settings.MAX_RETRY_ATTEMPTS:
        logger.info(f"ROUTING: No relevant docs found. Retry count {retry_count}/{settings.MAX_RETRY_ATTEMPTS}. Routing to rewrite_query.")
        return "rewrite_query"
        
    # If we've exhausted retries, go to generation (which will output the fallback answer)
    # We route to generate_answer instead of a dedicated fallback node because generate_answer
    # already has the logic to handle empty docs gracefully.
    logger.info(f"ROUTING: Exhausted retries ({retry_count}). Routing to generate_answer for fallback.")
    return "generate_answer"
