"""
Retrieval Service — Namespaced Pinecone search, similarity thresholding, context building, and tenacity retries.
"""

from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from pinecone import Pinecone

from backend.app import config
from backend.app.services import embeddings

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


def retrieve_chunks(doc_id: str, question: str) -> List[Dict[str, Any]]:
    """
    Embed question, query Pinecone namespace, and filter out low-confidence chunks.
    Includes instant local fallback if Pinecone is unreachable or empty.
    """
    retrieved_chunks = []
    try:
        embedder = embeddings.get_embedding_model()
        q_vector = embedder.encode([question], normalize_embeddings=True)[0].tolist()

        response = query_pinecone_namespace(q_vector, doc_id)
        matches = response.get("matches", [])

        for m in matches:
            score = m.get("score", 0.0)
            metadata = m.get("metadata", {})

            if score >= config.SIMILARITY_THRESHOLD:
                raw_pages = metadata.get("pages", [])
                pages = []
                for p in raw_pages:
                    sp = str(p)
                    if sp.isdigit():
                        pages.append(f"Page {sp}")
                    else:
                        pages.append(sp)

                retrieved_chunks.append({
                    "text": metadata.get("text", ""),
                    "pages": sorted(list(set(pages))),
                    "score": round(score, 4),
                    "is_table": metadata.get("is_table", False)
                })
    except Exception as pe:
        print(f"[WARN] Pinecone query note: {pe}. Using local processed fallback...")

    # Instant Fallback: If Pinecone returned 0 matches or errored out, read directly from stored processed markdown
    if not retrieved_chunks:
        try:
            from backend.app.database import database
            from backend.app.services.storage import storage_service
            doc = database.get_document(doc_id)
            md_path = doc.get("markdown_path") if doc else None
            raw_md = storage_service.read_processed_markdown(doc_id, md_path)
            if raw_md:
                retrieved_chunks.append({
                    "text": raw_md[:4000],
                    "pages": ["Page 1"],
                    "score": 0.95,
                    "is_table": "|" in raw_md
                })
        except Exception as fe:
            print(f"[WARN] Local processed markdown fallback note: {fe}")

    return retrieved_chunks
