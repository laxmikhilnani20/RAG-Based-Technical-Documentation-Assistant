import logging
from fastapi import APIRouter, HTTPException, Query
from app.api.models import DocumentsResponse, DocumentChunk
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/documents", response_model=DocumentsResponse, summary="List indexed documents in the corpus")
async def list_documents(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of chunks to return"),
    offset: int = Query(0, ge=0, description="Number of chunks to skip")
):
    logger.info(f"Fetching documents (limit={limit}, offset={offset})")
    
    try:
        vector_store = get_vector_store()
        # The underlying Chroma collection allows fetching with limit/offset
        collection = vector_store._collection
        
        # Get data from Chroma directly
        result = collection.get(
            limit=limit,
            offset=offset,
            include=["metadatas", "documents"]
        )
        
        chunks = []
        for i in range(len(result["ids"])):
            content = result["documents"][i]
            # Create a 100 char preview
            preview = content[:100] + "..." if len(content) > 100 else content
            
            chunk = DocumentChunk(
                id=result["ids"][i],
                content_preview=preview,
                metadata=result["metadatas"][i] or {}
            )
            chunks.append(chunk)
            
        # Get total count (Chroma's count() is fast)
        total_count = collection.count()
        
        return DocumentsResponse(
            total_chunks=total_count,
            chunks=chunks
        )
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
