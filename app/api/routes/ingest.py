import logging
from fastapi import APIRouter, HTTPException
from app.api.models import IngestURLRequest, IngestResponse
from app.rag.ingestion import ingest_urls

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, summary="Ingest new documents from URLs")
async def ingest_documents(request: IngestURLRequest):
    logger.info(f"Received request to ingest {len(request.urls)} URLs")
    
    # Convert HttpUrl objects to standard strings for the LangChain loader
    string_urls = [str(url) for url in request.urls]
    
    try:
        # Run the ingestion synchronously for now (could be sent to a background task in production)
        result = ingest_urls(string_urls)
        
        return IngestResponse(
            status=result["status"],
            documents_ingested=result["documents_ingested"],
            chunks_created=result["chunks_created"],
            collection=result["collection"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
