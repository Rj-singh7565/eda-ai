"""
High-Performance Semantic & Query Plan Cache with Thread-Safe Invalidation.

Provides:
- Exact-match fast path (<0.1ms) for both analytical query plans and RAG results.
- Vector cosine similarity matching (>= threshold) exclusively for DOCUMENT_RAG context.
- Safety: Strictly prohibits fuzzy semantic matching for analytical queries (prevents false positives on numerical thresholds).
- Document lifecycle invalidation: automatically cleared when documents are modified or deleted.
"""

import re
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import OrderedDict
import threading

from backend.app import config

logger = logging.getLogger("eda.cache")


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two normalized or un-normalized float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _normalize_query(query: str) -> str:
    """Normalize question by lowercasing, stripping extra whitespace and punctuation."""
    q = query.lower().strip()
    q = re.sub(r"[^\w\s><=!]", " ", q)
    return re.sub(r"\s+", " ", q).strip()


class SemanticCache:
    """Thread-safe LRU Semantic and Query Plan Cache."""

    def __init__(self, max_entries: int = 500, similarity_threshold: float = 0.96):
        self._lock = threading.Lock()
        self.max_entries = max_entries
        self.similarity_threshold = similarity_threshold
        # Key: (doc_id, engine, normalized_query) -> entry dict
        self._exact_cache: OrderedDict[Tuple[str, str, str], Dict[str, Any]] = OrderedDict()
        self.stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "invalidations": 0
        }

    def get(
        self,
        doc_id: str,
        query: str,
        engine: str = "DOCUMENT_RAG",
        query_vector: Optional[List[float]] = None
    ) -> Optional[Tuple[Any, str]]:
        """
        Lookup cached result.
        Returns:
            Tuple of (cached_data, hit_type) where hit_type is 'exact' or 'semantic',
            or None if cache miss.
        """
        norm_q = _normalize_query(query)
        cache_key = (doc_id, engine, norm_q)

        with self._lock:
            # Tier 1: Instant Exact Match (<0.1ms)
            if cache_key in self._exact_cache:
                self._exact_cache.move_to_end(cache_key)
                self.stats["exact_hits"] += 1
                logger.info(f"[CACHE HIT: EXACT] doc_id={doc_id} engine={engine} query='{query[:35]}'")
                return self._exact_cache[cache_key]["result"], "exact"

            # Tier 2: Semantic Similarity Match (strictly for DOCUMENT_RAG only)
            if engine == "DOCUMENT_RAG" and query_vector is not None:
                best_score = 0.0
                best_entry = None
                best_key = None

                for key, entry in self._exact_cache.items():
                    if key[0] == doc_id and key[1] == engine:
                        cached_vec = entry.get("vector")
                        if cached_vec:
                            sim = _cosine_similarity(query_vector, cached_vec)
                            if sim > best_score:
                                best_score = sim
                                best_entry = entry
                                best_key = key

                if best_entry and best_score >= self.similarity_threshold:
                    if best_key:
                        self._exact_cache.move_to_end(best_key)
                    self.stats["semantic_hits"] += 1
                    logger.info(f"[CACHE HIT: SEMANTIC] doc_id={doc_id} sim={best_score:.4f} threshold={self.similarity_threshold}")
                    return best_entry["result"], "semantic"

            self.stats["misses"] += 1
            return None

    def set(
        self,
        doc_id: str,
        query: str,
        result: Any,
        engine: str = "DOCUMENT_RAG",
        query_vector: Optional[List[float]] = None
    ):
        """Insert or update a cache entry in LRU order."""
        norm_q = _normalize_query(query)
        cache_key = (doc_id, engine, norm_q)

        with self._lock:
            if cache_key in self._exact_cache:
                self._exact_cache.move_to_end(cache_key)
            self._exact_cache[cache_key] = {
                "result": result,
                "vector": query_vector,
                "timestamp": time.time(),
                "query": query
            }

            # Enforce capacity
            while len(self._exact_cache) > self.max_entries:
                self._exact_cache.popitem(last=False)

    def invalidate_document(self, doc_id: str):
        """Invalidate all cached items for a specific document."""
        with self._lock:
            keys_to_remove = [k for k in self._exact_cache.keys() if k[0] == doc_id]
            for k in keys_to_remove:
                del self._exact_cache[k]
            self.stats["invalidations"] += len(keys_to_remove)
            logger.info(f"[CACHE INVALIDATION] Purged {len(keys_to_remove)} entries for doc_id={doc_id}")

    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self._exact_cache.clear()


# Global Singleton Cache Instance
semantic_cache = SemanticCache(
    max_entries=config.SEMANTIC_CACHE_MAX_ENTRIES,
    similarity_threshold=config.SIMILARITY_CACHE_THRESHOLD
)
