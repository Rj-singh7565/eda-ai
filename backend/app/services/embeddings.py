"""
Embedding Service — SentenceTransformer model manager with startup pre-warming.
"""

from backend.app import config

_embedding_model = None


def get_embedding_model():
    """Load SentenceTransformer model lazily or return cached instance."""
    global _embedding_model
    if _embedding_model is None:
        print("[EMBEDDINGS] Loading BAAI/bge-small-en-v1.5 embedding model into memory...")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        print("[EMBEDDINGS] Embedding model successfully loaded.")
    return _embedding_model


def warmup_embeddings():
    """Pre-warm embedding model at server startup."""
    model = get_embedding_model()
    # Execute quick sample encode to warm PyTorch JIT execution
    model.encode(["warmup query"], normalize_embeddings=True)
    print("[EMBEDDINGS] Warmup complete.")

