import sys
import os
import logging
from dotenv import load_dotenv

# Ensure the 'app' module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables explicitly before importing app modules
load_dotenv()

from app.rag.ingestion import ingest_urls

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# The corpus URLs we decided on
# Reduced to 4 URLs to stay safely under Gemini free tier limits (100 RPM)
CORPUS_URLS = [
    # LangGraph Docs
    "https://langchain-ai.github.io/langgraph/concepts/low_level/",
    "https://langchain-ai.github.io/langgraph/concepts/high_level/",
    
    # LangChain Docs
    "https://python.langchain.com/docs/concepts/rag/",
    
    # FastAPI Docs
    "https://fastapi.tiangolo.com/tutorial/first-steps/"
]

def main():
    logger.info("Starting documentation ingestion script...")
    
    try:
        result = ingest_urls(CORPUS_URLS)
        logger.info("Ingestion completed successfully!")
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
