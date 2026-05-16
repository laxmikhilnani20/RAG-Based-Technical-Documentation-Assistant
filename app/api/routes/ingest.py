import os
import shutil
import tempfile
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from app.api.models import IngestURLRequest, IngestResponse
from app.rag.ingestion import ingest_urls, ingest_file

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, summary="Ingest new documents from URLs")
async def ingest_documents(request: IngestURLRequest, x_api_key: Optional[str] = Header(None)):
    logger.info(f"Received request to ingest {len(request.urls)} URLs")
    
    if x_api_key:
        masked_key = f"{x_api_key[:6]}...{x_api_key[-4:]}"
        logger.info(f"Using user-provided API key: {masked_key}")
    else:
        logger.warning("No API key provided in request headers!")
    
    # Convert HttpUrl objects to standard strings for the LangChain loader
    string_urls = [str(url) for url in request.urls]
    
    try:
        # Run the ingestion synchronously for now
        result = ingest_urls(string_urls, api_key=x_api_key)
        
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

@router.post("/ingest/file", response_model=IngestResponse, summary="Ingest a new document from a file upload")
async def ingest_file_upload(file: UploadFile = File(...), x_api_key: Optional[str] = Header(None)):
    logger.info(f"Received request to ingest file: {file.filename}")
    
    if x_api_key:
        masked_key = f"{x_api_key[:6]}...{x_api_key[-4:]}"
        logger.info(f"Using user-provided API key: {masked_key}")
    else:
        logger.warning("No API key provided in request headers!")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported for upload.")
        
    try:
        # Save uploaded file to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ingest the temp file
        result = ingest_file(temp_path, source_name=file.filename, api_key=x_api_key)
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return IngestResponse(
            status=result["status"],
            documents_ingested=result["documents_ingested"],
            chunks_created=result["chunks_created"],
            collection=result["collection"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Error during file ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {str(e)}")
