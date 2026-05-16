from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_embeddings(api_key: str = None) -> GoogleGenerativeAIEmbeddings:
    """
    Initializes and returns the Gemini embedding model.
    """
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.error("API key was not provided by the user.")
        raise ValueError("A valid Gemini API Key must be provided by the user.")

    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBEDDING_MODEL,
        google_api_key=api_key
    )
