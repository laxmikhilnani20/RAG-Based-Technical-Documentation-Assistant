import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.routes import query, ingest, documents, feedback

# Configure basic structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="RAG Technical Documentation Assistant",
    description="A self-corrective LangGraph-based RAG API using FastAPI and Google Gemini.",
    version="1.0.0"
)

# CORS configuration (allow any for easy local development, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Root endpoint serves the UI
@app.get("/", summary="Chat UI")
async def root():
    return FileResponse("app/static/index.html")

# Health check (specifically required for Docker/HF Spaces)
@app.get("/health", summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "environment": settings.APP_ENV}

# Mount routers
app.include_router(query.router, tags=["Query"])
app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(feedback.router, tags=["Feedback"])

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
