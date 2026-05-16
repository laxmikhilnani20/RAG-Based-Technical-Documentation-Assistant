import uuid
import logging
from fastapi import APIRouter, HTTPException
from app.api.models import QueryRequest, QueryResponse, Citation
from app.graph.workflow import graph_app
from app.graph.state import RAGState

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=QueryResponse, summary="Submit a question to the assistant")
async def query_assistant(request: QueryRequest):
    logger.info(f"Received query: {request.question}")
    
    # Initialize the state for the LangGraph workflow
    initial_state: RAGState = {
        "question": request.question,
        "rewritten_query": "",
        "query_type": "unknown",
        "retrieved_docs": [],
        "graded_docs": [],
        "generation": "",
        "citations": [],
        "retry_count": 0,
        "answer_found": False,
        "session_id": request.session_id or str(uuid.uuid4())
    }
    
    try:
        # Execute the LangGraph workflow
        # .invoke runs the state machine from start to END
        final_state = graph_app.invoke(initial_state)
        
        # Format the citations from dictionaries back to the Pydantic models
        formatted_citations = [
            Citation(
                document=cit["document"],
                url=cit["url"],
                chunk_preview=cit["chunk_preview"]
            )
            for cit in final_state.get("citations", [])
        ]
        
        # Build the response
        response = QueryResponse(
            answer=final_state.get("generation", "Error generating answer."),
            sources=formatted_citations,
            query_type=final_state.get("query_type", "unknown"),
            retries_used=final_state.get("retry_count", 0),
            session_id=final_state.get("session_id")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error executing RAG pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the query: {str(e)}")
