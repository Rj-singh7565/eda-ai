"""
Embedding Service — SentenceTransformer model manager.
"""

from backend.app import config

_embedding_model = None


def get_embedding_model():
    """Load SentenceTransformer model lazily."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _embedding_model
