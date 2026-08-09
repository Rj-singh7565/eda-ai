"""
Ingestion Engine — Table-aware PDF parsing, sentence-aware chunking, and background embedding/indexing pipeline.
"""

import re
import os
import traceback
from typing import List, Dict, Any
from pypdf import PdfReader

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    pdfplumber = None
    HAS_PDFPLUMBER = False

import config
import database

# Lazy-loaded embedding model handle
_embedding_model = None

def get_embedding_model():
    """Load SentenceTransformer model lazily."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _embedding_model


def extract_table_as_markdown(table: List[List[Any]]) -> str:
    """Convert a raw pdfplumber table matrix into a Markdown formatted table."""
    if not table or not any(table):
        return ""
    
    # Filter out empty rows
    clean_rows = []
    for row in table:
        if row and any(cell is not None and str(cell).strip() for cell in row):
            clean_rows.append([str(cell).strip().replace("\n", " ") if cell is not None else "" for cell in row])
            
    if not clean_rows:
        return ""
        
    headers = clean_rows[0]
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in clean_rows[1:]:
        # Adjust row length if mismatched with headers
        if len(row) < len(headers):
            row.extend([""] * (len(headers) - len(row)))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        markdown += "| " + " | ".join(row) + " |\n"
        
    return markdown


def extract_pages_with_tables(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text and structured tables per page.
    Combines pdfplumber for table detection and PyPDF for text extraction.
    """
    pages_data = []
    
    # Open with pdfplumber to extract tables (if available)
    tables_per_page = {}
    if HAS_PDFPLUMBER and pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    extracted_tables = page.extract_tables()
                    md_tables = []
                    for tbl in extracted_tables:
                        md_tbl = extract_table_as_markdown(tbl)
                        if md_tbl:
                            md_tables.append(md_tbl)
                    if md_tables:
                        tables_per_page[i] = md_tables
        except Exception as e:
            print(f"[INGESTION] pdfplumber table extraction warning: {e}")

    # Read page text with PyPDF
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        tables = tables_per_page.get(i, [])
        if text or tables:
            pages_data.append({
                "page": i,
                "text": text,
                "tables": tables
            })
            
    return pages_data


def chunk_text_sentence_aware(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Sentence and paragraph-aware chunker that preserves table structure.
    Does not slice sentences or tables mid-way.
    """
    chunks = []
    
    for page_data in pages_data:
        page_num = page_data["page"]
        
        # 1. Process Table Chunks (preserve full markdown tables)
        for tbl_idx, table_md in enumerate(page_data.get("tables", [])):
            chunks.append({
                "text": f"Table on Page {page_num}:\n{table_md}",
                "pages": [page_num],
                "is_table": True
            })

        # 2. Process Narrative Text Chunks
        raw_text = page_data.get("text", "")
        if not raw_text:
            continue
            
        # Split text into paragraphs
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        current_chunk = ""
        
        for para in paragraphs:
            # If paragraph fits inside remaining chunk space
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                # If current chunk has accumulated content, push it
                if current_chunk:
                    chunks.append({
                        "text": current_chunk,
                        "pages": [page_num],
                        "is_table": False
                    })
                    
                # If individual paragraph is longer than chunk_size, split by sentences
                if len(para) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    sub_chunk = ""
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) + 1 <= chunk_size:
                            sub_chunk = f"{sub_chunk} {sentence}".strip()
                        else:
                            if sub_chunk:
                                chunks.append({
                                    "text": sub_chunk,
                                    "pages": [page_num],
                                    "is_table": False
                                })
                            sub_chunk = sentence
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para
                    
        if current_chunk:
            chunks.append({
                "text": current_chunk,
                "pages": [page_num],
                "is_table": False
            })

    return chunks


def run_ingestion_pipeline(doc_id: str, pdf_path: str):
    """
    Async background task executing the full ingestion workflow:
    parse -> chunk -> embed -> Pinecone upsert under namespace=doc_id.
    """
    try:
        # Phase 1: Parsing
        database.update_document_status(doc_id, "parsing")
        pages_data = extract_pages_with_tables(pdf_path)
        page_count = len(pages_data)
        database.update_document_status(doc_id, "parsing", page_count=page_count)

        if not pages_data:
            database.update_document_status(
                doc_id, "failed", error_message="No extractable text or tables found in PDF."
            )
            return

        # Phase 2: Chunking
        database.update_document_status(doc_id, "chunking")
        chunks = chunk_text_sentence_aware(pages_data)
        chunk_count = len(chunks)
        database.update_document_status(doc_id, "chunking", chunk_count=chunk_count)

        if not chunks:
            database.update_document_status(
                doc_id, "failed", error_message="Failed to generate chunks from PDF."
            )
            return

        # Phase 3: Embedding
        database.update_document_status(doc_id, "embedding")
        embedder = get_embedding_model()
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.encode(texts_to_embed, show_progress_bar=False, normalize_embeddings=True).tolist()

        # Phase 4: Pinecone Vector Storage (Namespaced)
        database.update_document_status(doc_id, "indexing")
        
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        
        # Ensure Pinecone index exists with matching dimension
        existing_indexes = {idx.name: idx for idx in pc.list_indexes()}
        if config.PINECONE_INDEX_NAME in existing_indexes:
            idx_info = existing_indexes[config.PINECONE_INDEX_NAME]
            if getattr(idx_info, "dimension", None) and idx_info.dimension != config.EMBEDDING_DIMENSION:
                print(f"[PINECONE] Dimension mismatch: index is {idx_info.dimension}, model requires {config.EMBEDDING_DIMENSION}. Recreating index...")
                pc.delete_index(config.PINECONE_INDEX_NAME)
                import time
                time.sleep(2)
                pc.create_index(
                    name=config.PINECONE_INDEX_NAME,
                    dimension=config.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
        else:
            pc.create_index(
                name=config.PINECONE_INDEX_NAME,
                dimension=config.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        index = pc.Index(config.PINECONE_INDEX_NAME)
        
        # Prepare vectors for upsert under namespace=doc_id
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{doc_id}-chunk-{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "pages": [str(p) for p in chunk["pages"]],
                    "is_table": chunk.get("is_table", False),
                    "doc_id": doc_id
                }
            })

        # Upsert in batches of 100
        batch_size = 100
        for b_start in range(0, len(vectors), batch_size):
            batch = vectors[b_start : b_start + batch_size]
            index.upsert(vectors=batch, namespace=doc_id)

        # Mark ready
        database.update_document_status(doc_id, "ready")
        print(f"[INGESTION SUCCESS] Document {doc_id} processed: {page_count} pages, {chunk_count} chunks indexed.")

    except Exception as e:
        error_msg = f"Ingestion error: {str(e)}"
        print(f"[INGESTION ERROR] Document {doc_id}: {error_msg}")
        traceback.print_exc()
        database.update_document_status(doc_id, "failed", error_message=error_msg)
