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
        "storage": config.STORAGE_TYPE
    }
