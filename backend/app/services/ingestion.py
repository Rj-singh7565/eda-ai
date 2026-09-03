"""
Ingestion Service — Multi-format parsing, magic byte detection, Markdown normalization, and Pinecone vector indexing.
"""

import os
import zipfile
import traceback
from typing import List, Dict, Any

from pinecone import Pinecone, ServerlessSpec

from backend.app import config
from backend.app.database import database
from backend.app.services.storage import storage_service
from backend.app.services import extraction, normalization, chunking, embeddings


def detect_file_type(file_path: str) -> str:
    """
    Detect file format using magic bytes signature inspection with fallback to file extension.
    Returns one of: 'pdf', 'docx', 'pptx', 'excel', 'csv', 'txt', 'md', 'image', 'zip', or 'unknown'.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    text_exts = {
        ".txt", ".log", ".md", ".markdown", ".json", ".tsv", ".html", ".htm",
        ".xml", ".py", ".js", ".ts", ".jsx", ".tsx", ".yaml", ".yml", ".rst",
        ".rtf", ".ini", ".conf", ".css", ".sql", ".sh", ".bat"
    }
    valid_exts = {
        ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv", ".png", ".jpg",
        ".jpeg", ".bmp", ".tiff", ".zip"
    }.union(text_exts)

    if ext not in valid_exts:
        return "unknown"
    
    try:
        with open(file_path, "rb") as f:
            header = f.read(2048)
    except Exception:
        header = b""

    # Magic Bytes Inspections
    if header.startswith(b"%PDF-"):
        return "pdf"

    if header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff") or header.startswith(b"GIF8") or header.startswith(b"BM"):
        return "image"

    # Zip-based archives (ZIP, DOCX, PPTX, XLSX)
    if header.startswith(b"PK\x03\x04"):
        if ext == ".docx":
            return "docx"
        elif ext == ".pptx":
            return "pptx"
        elif ext in (".xlsx", ".xls"):
            return "excel"
        elif ext == ".zip":
            return "zip"
        else:
            try:
                with zipfile.ZipFile(file_path, 'r') as z:
                    names = z.namelist()
                    if "word/document.xml" in names:
                        return "docx"
                    if "ppt/presentation.xml" in names:
                        return "pptx"
                    if "xl/workbook.xml" in names:
                        return "excel"
            except Exception:
                pass
            return "zip"

    if ext == ".pdf":
        return "pdf"
    elif ext == ".docx":
        return "docx"
    elif ext == ".pptx":
        return "pptx"
    elif ext in (".xlsx", ".xls"):
        return "excel"
    elif ext == ".csv":
        return "csv"
    elif ext in text_exts:
        return "md" if ext in (".md", ".markdown") else "txt"
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        return "image"
    elif ext == ".zip":
        return "zip"

    try:
        header.decode('utf-8')
        return "md" if ext in (".md", ".markdown") else "txt"
    except UnicodeDecodeError:
        pass

    return "unknown"


def extract_by_type(file_path: str, file_type: str) -> List[Dict[str, Any]]:
    """Central router dispatching to format-specific extractors."""
    if file_type == "pdf":
        return extraction.extract_pdf(file_path)
    elif file_type == "docx":
        return extraction.extract_docx(file_path)
    elif file_type == "pptx":
        return extraction.extract_pptx(file_path)
    elif file_type == "excel":
        return extraction.extract_excel(file_path)
    elif file_type == "csv":
        return extraction.extract_csv(file_path)
    elif file_type in ("txt", "md"):
        return extraction.extract_txt_md(file_path)
    elif file_type == "image":
        return extraction.extract_image_ocr(file_path)
    else:
        raise ValueError(f"Unsupported extraction format '{file_type}'.")


def run_ingestion_pipeline(doc_id: str, file_path: str, file_type: str = "pdf"):
    """
    Complete background ingestion pipeline:
    parsing -> normalizing -> chunking -> embedding -> indexing -> ready (or failed)
    """
    doc = database.get_document(doc_id)
    original_filename = doc["filename"] if doc else os.path.basename(file_path)

    try:
        # Phase 1: Parsing
        database.update_document_status(doc_id, "parsing")
        pages_data = extract_by_type(file_path, file_type)

        if not pages_data:
            database.update_document_status(
                doc_id, "failed", error_message="No text or tabular data could be extracted from document."
            )
            return

        # Phase 2: Normalization
        database.update_document_status(doc_id, "normalizing")
        canonical_md = normalization.normalize_to_markdown(doc_id, original_filename, file_type, pages_data)
        saved_md_path = storage_service.save_processed_markdown(doc_id, canonical_md)

        # Phase 3: Chunking
        database.update_document_status(doc_id, "chunking")
        chunks = chunking.chunk_markdown(canonical_md, doc_id)

        if not chunks:
            database.update_document_status(
                doc_id, "failed", error_message="Document text was parsed but produced zero indexable chunks."
            )
            return

        # Phase 4: Embedding with hardware acceleration and SHA-256 caching
        database.update_document_status(doc_id, "embedding")
        texts_to_embed = [c["text"] for c in chunks]
        vectors = embeddings.generate_embeddings(texts_to_embed)

        # Phase 5: Indexing to Pinecone (Batch upserts)
        database.update_document_status(doc_id, "indexing")
        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        index_name = config.PINECONE_INDEX_NAME

        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing_indexes:
            try:
                pc.create_index(
                    name=index_name,
                    dimension=config.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            except Exception as ie:
                print(f"[PINECONE] Create index note: {ie}")

        index = pc.Index(index_name)

        # Handle index dimension mismatch safely
        try:
            desc = index.describe_index_stats()
            curr_dim = desc.get("dimension")
            if curr_dim and curr_dim != config.EMBEDDING_DIMENSION:
                print(f"[WARN] Pinecone index dimension mismatch ({curr_dim} vs {config.EMBEDDING_DIMENSION}). Recreating index...")
                pc.delete_index(index_name)
                pc.create_index(
                    name=index_name,
                    dimension=config.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                index = pc.Index(index_name)
        except Exception as e:
            print(f"[WARN] Failed to check Pinecone index dimension: {e}")

        # Batch upsert vectors into doc_id namespace (batch_size = 200)
        pinecone_vectors = []
        seen_vector_ids = set()
        for c, vec in zip(chunks, vectors):
            vec_id = str(c["chunk_id"])
            if vec_id in seen_vector_ids:
                continue
            seen_vector_ids.add(vec_id)

            raw_pages = c.get("pages", [])
            pages = [str(p) for p in raw_pages] if isinstance(raw_pages, list) else [str(raw_pages)]

            raw_page_numbers = c.get("page_numbers", [])
            if not isinstance(raw_page_numbers, list):
                raw_page_numbers = [raw_page_numbers]

            page_numbers = []
            for p in raw_page_numbers:
                try:
                    clean_str = str(p).strip().strip("[]'\"")
                    clean_p = str(int(float(clean_str)))
                except Exception:
                    clean_p = str(p)
                page_numbers.append(clean_p)

            pinecone_vectors.append({
                "id": vec_id,
                "values": vec,
                "metadata": {
                    "doc_id": str(doc_id),
                    "filename": str(original_filename),
                    "pages": pages,
                    "page_numbers": page_numbers,
                    "is_table": bool(c.get("is_table", False)),
                    "text": str(c.get("text", ""))[:1500]
                }
            })

        upsert_batch_size = 200
        for i in range(0, len(pinecone_vectors), upsert_batch_size):
            batch = pinecone_vectors[i:i + upsert_batch_size]
            index.upsert(vectors=batch, namespace=doc_id)

        # Phase 6: Ready!
        database.update_document_status(
            doc_id,
            "ready",
            page_count=len(pages_data),
            chunk_count=len(chunks),
            markdown_path=saved_md_path
        )
        print(f"[INGESTION SUCCESS] Document {doc_id} ('{original_filename}') fully ingested ({len(chunks)} chunks).")

    except Exception as e:
        error_msg = f"Ingestion error: {str(e)}"
        print(f"[INGESTION FAILED] Doc {doc_id}: {error_msg}")
        traceback.print_exc()
        database.update_document_status(doc_id, "failed", error_message=error_msg)
