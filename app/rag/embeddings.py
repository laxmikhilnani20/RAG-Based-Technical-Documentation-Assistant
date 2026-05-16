from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Initializes and returns the Gemini embedding model.
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        logger.error("GEMINI_API_KEY is missing or not set properly in the environment.")
        raise ValueError("Valid GEMINI_API_KEY is required to initialize embeddings.")

    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY
    )
