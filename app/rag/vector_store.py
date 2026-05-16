import os
import chromadb
from langchain_chroma import Chroma
from app.config import settings
from app.rag.embeddings import get_embeddings
import logging

logger = logging.getLogger(__name__)

def get_vector_store() -> Chroma:
    """
    Initializes and returns the Chroma vector store instance.
    """
    embeddings = get_embeddings()
    
    # Ensure the directory exists
    os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
    
    # Initialize the underlying chromadb client explicitly for persistent storage
    persistent_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    
    # Wrap it in LangChain's Chroma wrapper
    vector_store = Chroma(
        client=persistent_client,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings
    )
    
    return vector_store

def get_retriever():
    """
    Returns a configured retriever from the vector store.
    """
    vector_store = get_vector_store()
    return vector_store.as_retriever(
        search_kwargs={"k": settings.RETRIEVAL_TOP_K}
    )
