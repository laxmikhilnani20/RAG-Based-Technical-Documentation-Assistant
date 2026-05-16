# ============================================================
# Dockerfile
# RAG-Based Technical Documentation Assistant
# ============================================================
# Base image: Python 3.11 slim for minimal size
# Port 7860 is REQUIRED for Hugging Face Spaces Docker SDK
# ============================================================

FROM python:3.11-slim

# ------------------------------------------------------------
# Set working directory inside the container
# ------------------------------------------------------------
WORKDIR /app

# ------------------------------------------------------------
# Set environment variables
# Prevents Python from writing .pyc files
# Ensures stdout/stderr are not buffered (good for logs)
# ------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ------------------------------------------------------------
# Install system dependencies
# (needed by ChromaDB and some Python packages)
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Copy and install Python dependencies first
# (Docker layer caching — only reinstalls if requirements change)
# ------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# Copy the application source code
# ------------------------------------------------------------
COPY . .

# ------------------------------------------------------------
# Copy pre-built ChromaDB vector store (baked into image)
# This avoids re-ingestion on every container start
# ------------------------------------------------------------
# COPY chroma_db/ ./chroma_db/

# ------------------------------------------------------------
# Expose port — 7860 is mandatory for Hugging Face Spaces
# Use 8000 for local development
# ------------------------------------------------------------
EXPOSE 7860

# ------------------------------------------------------------
# Run the FastAPI app with Uvicorn
# app.main:app → file: app/main.py, FastAPI instance: app
# ------------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
