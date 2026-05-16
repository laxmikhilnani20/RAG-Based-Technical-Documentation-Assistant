import hashlib
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import bs4
from app.config import settings
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

def generate_chunk_id(url: str, chunk_index: int) -> str:
    """
    Generates a deterministic ID for a chunk based on its source URL and index.
    This ensures that re-ingesting the same URL overwrites the old chunks.
    """
    hash_input = f"{url}_{chunk_index}".encode("utf-8")
    return hashlib.md5(hash_input).hexdigest()

def ingest_urls(urls: List[str]) -> Dict[str, Any]:
    """
    Fetches, chunks, and indexes a list of URLs into ChromaDB.
    Returns statistics about the ingestion process.
    """
    logger.info(f"Starting ingestion for {len(urls)} URLs")
    
    # 1. Load Documents
    # We use bs4_strainer to parse only the main content if possible, but for generic
    # documentation, grabbing everything is often safest. 
    # To avoid headers/footers noise, one might customize the strainer per site, 
    # but for this assignment, standard parsing is sufficient.
    loader = WebBaseLoader(web_paths=urls)
    docs = loader.load()
    logger.info(f"Loaded {len(docs)} documents from URLs")
    
    # 2. Split Documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(docs)
    logger.info(f"Created {len(chunks)} chunks")
    
    # 3. Assign Deterministic IDs and Metadata
    ids = []
    for i, chunk in enumerate(chunks):
        # Ensure source URL is in metadata
        source_url = chunk.metadata.get("source", "unknown")
        
        # We use a running index 'i' to guarantee uniqueness per ingestion batch,
        # but realistically, grouping by source URL and numbering within that URL is better.
        # Let's count indices per URL to be perfectly deterministic.
        pass

    # Better approach for IDs: Count per source
    url_counts = {}
    final_chunks = []
    ids = []
    
    for chunk in chunks:
        source_url = chunk.metadata.get("source", "unknown")
        if source_url not in url_counts:
            url_counts[source_url] = 0
            
        chunk_idx = url_counts[source_url]
        url_counts[source_url] += 1
        
        chunk_id = generate_chunk_id(source_url, chunk_idx)
        ids.append(chunk_id)
        
        # Add extra metadata for our specific needs
        chunk.metadata["chunk_index"] = chunk_idx
        chunk.metadata["source_type"] = "web"
        
        final_chunks.append(chunk)

    # 4. Store in ChromaDB
    vector_store = get_vector_store()
    
    # Add documents with explicit IDs to handle upserts natively
    vector_store.add_documents(documents=final_chunks, ids=ids)
    logger.info(f"Successfully stored {len(final_chunks)} chunks in ChromaDB")
    
    return {
        "status": "success",
        "documents_ingested": len(docs),
        "chunks_created": len(final_chunks),
        "collection": settings.CHROMA_COLLECTION_NAME,
        "message": f"Successfully ingested {len(docs)} documents into {len(final_chunks)} chunks."
    }

def ingest_file(file_path: str, source_name: str) -> Dict[str, Any]:
    """
    Ingests a single local file (e.g., PDF) into ChromaDB.
    """
    logger.info(f"Starting ingestion for file: {file_path}")
    
    # Determine loader
    if file_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        # Fallback to a basic text loader if needed, but PyPDF is primary for this scope.
        raise ValueError("Currently only PDF file ingestion is implemented locally.")
        
    docs = loader.load()
    
    # Standardize metadata source to be the filename rather than the local path
    for doc in docs:
        doc.metadata["source"] = source_name
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(docs)
    
    url_counts = {}
    ids = []
    
    for chunk in chunks:
        source = chunk.metadata.get("source", source_name)
        if source not in url_counts:
            url_counts[source] = 0
            
        chunk_idx = url_counts[source]
        url_counts[source] += 1
        
        chunk_id = generate_chunk_id(source, chunk_idx)
        ids.append(chunk_id)
        chunk.metadata["chunk_index"] = chunk_idx
        chunk.metadata["source_type"] = "file"

    vector_store = get_vector_store()
    vector_store.add_documents(documents=chunks, ids=ids)
    
    return {
        "status": "success",
        "documents_ingested": len(docs), # For PDF, this is often pages
        "chunks_created": len(chunks),
        "collection": settings.CHROMA_COLLECTION_NAME,
        "message": f"Successfully ingested {source_name} into {len(chunks)} chunks."
    }
