from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM Settings
    GEMINI_LLM_MODEL: str = "models/gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-2"

    # ChromaDB Settings
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "technical_docs"

    # RAG Settings
    RETRIEVAL_TOP_K: int = 2
    MAX_RETRY_ATTEMPTS: int = 2
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # API Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Global settings instance
settings = Settings()
