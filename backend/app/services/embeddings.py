"""
Embedding Service — Hardware-adaptive SentenceTransformer embedding manager with SHA-256 deduplication and memory caching.
"""

import hashlib
import threading
from typing import List, Union
import torch

from backend.app import config

_embedding_model = None
_embedding_device = None
_model_lock = threading.Lock()
_EMBEDDING_CACHE: dict = {}  # sha256 -> list of float vectors (max 10,000 entries)
_MAX_CACHE_ENTRIES = 10000


def get_device() -> str:
    """Detect the best available compute device (CUDA GPU, MPS, or CPU)."""
    global _embedding_device
    if _embedding_device is None:
        if torch.cuda.is_available():
            _embedding_device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _embedding_device = "mps"
        else:
            _embedding_device = "cpu"
            # Set PyTorch thread count for optimal multi-threaded CPU matrix operations
            try:
                torch.set_num_threads(min(2, max(1, torch.get_num_threads())))
            except Exception:
                pass
        print(f"[EMBEDDINGS] Hardware compute device: {_embedding_device}")
    return _embedding_device


def get_embedding_model():
    """Load SentenceTransformer model lazily onto the optimal compute device with thread safety."""
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                device = get_device()
                print(f"[EMBEDDINGS] Loading {config.EMBEDDING_MODEL} on device '{device}'...")
                from sentence_transformers import SentenceTransformer
                try:
                    _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL, device=device, local_files_only=True)
                except Exception:
                    _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL, device=device)
                print("[EMBEDDINGS] Embedding model successfully loaded.")
    return _embedding_model


def _compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text for deduplication and caching."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def generate_embeddings(texts: List[str], batch_size: int = None) -> List[List[float]]:
    """
    Generate normalized dense vector embeddings with SHA-256 content deduplication and caching.
    Reuses existing embeddings for identical text and executes in optimal batch sizes.
    """
    if not texts:
        return []

    global _EMBEDDING_CACHE
    device = get_device()
    
    # Choose optimal hardware-adaptive batch size
    if batch_size is None:
        batch_size = 256 if device in ("cuda", "mps") else 128

    model = get_embedding_model()
    
    # 1. Hash texts and identify cache hits vs unique texts to embed
    hashes = [_compute_text_hash(t) for t in texts]
    unique_missing_texts = {}  # hash -> text
    results_by_hash = {}

    for text, h in zip(texts, hashes):
        if h in _EMBEDDING_CACHE:
            results_by_hash[h] = _EMBEDDING_CACHE[h]
        elif h not in unique_missing_texts:
            unique_missing_texts[h] = text

    # 2. Embed missing unique texts in batches
    if unique_missing_texts:
        missing_hashes = list(unique_missing_texts.keys())
        missing_texts = [unique_missing_texts[h] for h in missing_hashes]
        
        encoded_vectors = model.encode(
            missing_texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()

        # Evict cache if nearing upper threshold
        if len(_EMBEDDING_CACHE) + len(missing_hashes) > _MAX_CACHE_ENTRIES:
            # Drop oldest 30% of cache items
            drop_count = int(_MAX_CACHE_ENTRIES * 0.3)
            for k in list(_EMBEDDING_CACHE.keys())[:drop_count]:
                del _EMBEDDING_CACHE[k]

        for h, vec in zip(missing_hashes, encoded_vectors):
            _EMBEDDING_CACHE[h] = vec
            results_by_hash[h] = vec

    # 3. Assemble full results matching original input order
    return [results_by_hash[h] for h in hashes]


def generate_query_embedding(query: str) -> List[float]:
    """Generate a single normalized dense vector embedding for a search query."""
    embeddings = generate_embeddings([query])
    return embeddings[0] if embeddings else []


def warmup_embeddings():
    """Pre-warm embedding model at server startup."""
    model = get_embedding_model()
    generate_embeddings(["warmup query"])
    print("[EMBEDDINGS] Warmup complete.")


