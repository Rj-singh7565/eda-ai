"""
Healthcheck Route — System status and environment check.
"""

from fastapi import APIRouter
from backend.app import config

router = APIRouter()

@router.get("/health")
@router.get("/api/health")
async def health_check():
    """Health check endpoint returning system operational status."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "embedding_model": config.EMBEDDING_MODEL,
        "llm_model": config.LLM_MODEL,
        "pinecone_index": config.PINECONE_INDEX_NAME,
        "database": "postgresql" if config.DATABASE_URL and config.DATABASE_URL.startswith("postgres") else "sqlite",
        "storage": config.STORAGE_TYPE,
        "pinecone_configured": bool(config.PINECONE_API_KEY and config.PINECONE_API_KEY != "your_pinecone_api_key"),
        "groq_configured": bool(config.GROQ_API_KEY and config.GROQ_API_KEY != "your_groq_api_key")
    }
