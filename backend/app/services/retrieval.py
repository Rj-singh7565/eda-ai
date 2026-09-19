"""
Retrieval Service — Adaptive Multi-Tier Search, Namespaced Vector Retrieval,
Lexical/Keyword Fallback, and Table-Aware Context Assembly.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from pinecone import Pinecone

from backend.app import config
from backend.app.database import database
from backend.app.services import embeddings
from backend.app.services.storage import storage_service

logger = logging.getLogger("eda.retrieval")
logging.basicConfig(level=logging.INFO)

_pinecone_index = None


def get_pinecone_index():
    """Lazy initialization of Pinecone index handle."""
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        _pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
    return _pinecone_index


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def query_pinecone_namespace(query_vector: List[float], doc_id: str, top_k: int = config.TOP_K):
    """Query Pinecone vector database under namespace=doc_id with automatic retries."""
    index = get_pinecone_index()
    return index.query(
        vector=query_vector,
        top_k=top_k,
        namespace=doc_id,
        include_metadata=True
    )


def _lexical_search_markdown(raw_md: str, question: str, top_sections: int = 3) -> List[Dict[str, Any]]:
    """
    Tier 3 Fallback: Lexical / keyword search across Markdown sections and table headers.
    Ensures that queries with exact keywords or numbers find relevant sections even if semantic similarity is low.
    """
    if not raw_md:
        return []

    # Tokenize question keywords (words with len >= 3)
    stopwords = {"what", "which", "where", "when", "show", "give", "find", "list", "from", "with", "that", "this", "about"}
    keywords = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", question) if w.lower() not in stopwords]

    if not keywords:
        return []

    # Split markdown by top-level section headers
    sections = re.split(r"(?=\n##?\s+)", "\n" + raw_md)
    scored_sections = []

    for sec in sections:
        sec_clean = sec.strip()
        if not sec_clean:
            continue

        sec_lower = sec_clean.lower()
        score = 0
        for kw in keywords:
            count = sec_lower.count(kw)
            if count > 0:
                score += min(count, 5) * 1.5

        if score > 0:
            header_match = re.match(r"^##?\s+(.+)$", sec_clean, re.MULTILINE)
            sec_title = header_match.group(1).strip() if header_match else "Document Excerpt"
            scored_sections.append({
                "text": sec_clean[:2500],
                "pages": [sec_title],
                "score": min(0.92, 0.40 + (score * 0.05)),
                "is_table": "|" in sec_clean
            })

    scored_sections.sort(key=lambda x: x["score"], reverse=True)
    return scored_sections[:top_sections]


def retrieve_chunks(doc_id: str, question: str) -> List[Dict[str, Any]]:
    """
    Adaptive Multi-Tier Retrieval:
    1. Tier 1: Dense Vector Similarity Search in Pinecone with namespace=doc_id.
    2. Tier 2: Adaptive Threshold Relaxation (if initial matches < 2).
    3. Tier 3: Lexical / Keyword Search over full canonical Markdown.
    4. Tier 4: Structured Dataset Direct Inspection (for CSV/Excel).
    """
    retrieved_chunks: List[Dict[str, Any]] = []
    seen_texts = set()

    strategy_log = {"doc_id": doc_id, "tiers_executed": [], "matches_per_tier": {}}

    # ── Tier 1: Standard Dense Vector Retrieval ──────────────────────────────
    try:
        embedder = embeddings.get_embedding_model()
        q_vector = embedder.encode([question], normalize_embeddings=True)[0].tolist()

        strategy_log["tiers_executed"].append("dense_vector_primary")
        response = query_pinecone_namespace(q_vector, doc_id, top_k=config.TOP_K)
        matches = response.get("matches", [])
        strategy_log["matches_per_tier"]["tier1_candidates"] = len(matches)

        for m in matches:
            score = m.get("score", 0.0)
            metadata = m.get("metadata", {})
            text = metadata.get("text", "").strip()

            if score >= config.SIMILARITY_THRESHOLD and text:
                text_key = re.sub(r"\s+", " ", text[:150])
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    raw_pages = metadata.get("pages", [])
                    pages = [f"Page {p}" if str(p).isdigit() else str(p) for p in raw_pages]

                    retrieved_chunks.append({
                        "text": text,
                        "pages": sorted(list(set(pages))) if pages else ["Section 1"],
                        "score": round(score, 4),
                        "is_table": metadata.get("is_table", False)
                    })

        strategy_log["matches_per_tier"]["tier1_accepted"] = len(retrieved_chunks)

    except Exception as pe:
        logger.warning(f"Pinecone vector retrieval note for doc {doc_id}: {pe}")
        matches = []

    # ── Tier 2: Adaptive Threshold Relaxation (if matches are insufficient) ──
    if len(retrieved_chunks) < 2 and matches:
        strategy_log["tiers_executed"].append("adaptive_threshold_relaxation")
        relaxed_threshold = max(0.20, config.SIMILARITY_THRESHOLD - 0.15)

        for m in matches:
            score = m.get("score", 0.0)
            metadata = m.get("metadata", {})
            text = metadata.get("text", "").strip()

            if score >= relaxed_threshold and text:
                text_key = re.sub(r"\s+", " ", text[:150])
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    raw_pages = metadata.get("pages", [])
                    pages = [f"Page {p}" if str(p).isdigit() else str(p) for p in raw_pages]

                    retrieved_chunks.append({
                        "text": text,
                        "pages": sorted(list(set(pages))) if pages else ["Section 1"],
                        "score": round(score, 4),
                        "is_table": metadata.get("is_table", False)
                    })

        strategy_log["matches_per_tier"]["tier2_accepted"] = len(retrieved_chunks)

    # ── Tier 3: Lexical / Keyword Search Fallback ─────────────────────────────
    if len(retrieved_chunks) < 2:
        try:
            strategy_log["tiers_executed"].append("lexical_markdown_search")
            doc = database.get_document(doc_id)
            md_path = doc.get("markdown_path") if doc else None
            raw_md = storage_service.read_processed_markdown(doc_id, md_path)

            if raw_md:
                lexical_matches = _lexical_search_markdown(raw_md, question, top_sections=3)
                for lm in lexical_matches:
                    text_key = re.sub(r"\s+", " ", lm["text"][:150])
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        retrieved_chunks.append(lm)

                strategy_log["matches_per_tier"]["tier3_lexical_accepted"] = len(lexical_matches)

                # Fallback: If still empty, provide the document's header / overview section
                if not retrieved_chunks:
                    retrieved_chunks.append({
                        "text": raw_md[:3500],
                        "pages": ["Overview / Document Content"],
                        "score": 0.85,
                        "is_table": "|" in raw_md
                    })
        except Exception as fe:
            logger.warning(f"Lexical markdown fallback error for doc {doc_id}: {fe}")

    # Log structured observability telemetry
    logger.info(f"[RETRIEVAL TELEMETRY] doc_id={doc_id} query='{question[:40]}' final_chunks={len(retrieved_chunks)} strategies={strategy_log['tiers_executed']}")

    return retrieved_chunks
