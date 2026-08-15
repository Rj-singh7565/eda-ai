"""
Chunking Service — Sentence-aware & table-preserving chunking for canonical Markdown documents and raw pages.
"""

import re
from typing import List, Dict, Any
from backend.app import config


def chunk_markdown(
    markdown_text: str,
    doc_id_or_size: Any = "doc_id",
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Sentence-aware chunking preserving Markdown tables and section metadata headers.
    """
    if isinstance(doc_id_or_size, int):
        chunk_size = doc_id_or_size
        doc_id = "doc_id"
    else:
        doc_id = str(doc_id_or_size)

    content = re.sub(r"^---[\s\S]*?---\n*", "", markdown_text).strip()
    if not content:
        return []

    sections = re.split(r"(?=\n##?\s+)", "\n" + content)
    chunks = []
    chunk_idx = 1

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        header_match = re.match(r"^##?\s+(.+)$", sec, re.MULTILINE)
        section_label = header_match.group(1).strip() if header_match else "General"
        page_num_match = re.search(r"(\d+)", section_label)
        page_num = int(page_num_match.group(1)) if page_num_match else 1

        sec_body = re.sub(r"^##?\s+.+\n*", "", sec).strip()
        if not sec_body:
            continue

        table_blocks = []

        def replace_table(match):
            table_blocks.append(match.group(0).strip())
            return f"\n\n__TABLE_BLOCK_{len(table_blocks) - 1}__\n\n"

        table_pattern = r"(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)"
        text_with_table_tokens = re.sub(table_pattern, replace_table, sec_body)

        paragraphs = re.split(r"\n\s*\n", text_with_table_tokens)

        current_text = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if para.startswith("__TABLE_BLOCK_") and para.endswith("__"):
                tbl_index = int(para.replace("__TABLE_BLOCK_", "").replace("__", ""))
                tbl_content = table_blocks[tbl_index]

                if current_text.strip():
                    chunks.append({
                        "chunk_id": f"{doc_id}_{chunk_idx}",
                        "text": f"[{section_label}]\n" + current_text.strip(),
                        "pages": [section_label],
                        "page_labels": [section_label],
                        "page_numbers": [page_num],
                        "is_table": False
                    })
                    chunk_idx += 1
                    current_text = ""

                chunks.append({
                    "chunk_id": f"{doc_id}_{chunk_idx}",
                    "text": f"[{section_label} Table]\n" + tbl_content,
                    "pages": [section_label],
                    "page_labels": [section_label],
                    "page_numbers": [page_num],
                    "is_table": True
                })
                chunk_idx += 1
                continue

            for i, tbl_str in enumerate(table_blocks):
                para = para.replace(f"__TABLE_BLOCK_{i}__", "\n" + tbl_str + "\n")

            sentences = re.split(r"(?<=[.!?])\s+", para)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if len(current_text) + len(sentence) + 1 <= chunk_size:
                    current_text += (" " if current_text else "") + sentence
                else:
                    if current_text.strip():
                        chunks.append({
                            "chunk_id": f"{doc_id}_{chunk_idx}",
                            "text": f"[{section_label}]\n" + current_text.strip(),
                            "pages": [section_label],
                            "page_labels": [section_label],
                            "page_numbers": [page_num],
                            "is_table": False
                        })
                        chunk_idx += 1

                        overlap_start = max(0, len(current_text) - chunk_overlap)
                        current_text = current_text[overlap_start:] + " " + sentence
                    else:
                        current_text = sentence

        if current_text.strip():
            chunks.append({
                "chunk_id": f"{doc_id}_{chunk_idx}",
                "text": f"[{section_label}]\n" + current_text.strip(),
                "pages": [section_label],
                "page_labels": [section_label],
                "page_numbers": [page_num],
                "is_table": False
            })
            chunk_idx += 1

    return chunks


def chunk_text_sentence_aware(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """Legacy helper function chunking raw pages_data list."""
    chunks = []
    chunk_idx = 1

    for page_item in pages_data:
        page_num = page_item.get("page", 1)
        page_label = page_item.get("page_label", f"Page {page_num}")
        text = page_item.get("text", "").strip()
        tables = page_item.get("tables", [])

        for tbl in tables:
            chunks.append({
                "chunk_id": f"chunk_{chunk_idx}",
                "text": f"[{page_label} Table]\n{tbl}",
                "pages": [page_num],
                "page_labels": [page_label],
                "is_table": True
            })
            chunk_idx += 1

        if text:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            current_chunk = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    if current_chunk.strip():
                        chunks.append({
                            "chunk_id": f"chunk_{chunk_idx}",
                            "text": f"[{page_label}]\n{current_chunk.strip()}",
                            "pages": [page_num],
                            "page_labels": [page_label],
                            "is_table": False
                        })
                        chunk_idx += 1
                        overlap_start = max(0, len(current_chunk) - chunk_overlap)
                        current_chunk = current_chunk[overlap_start:] + " " + sentence
                    else:
                        current_chunk = sentence

            if current_chunk.strip():
                chunks.append({
                    "chunk_id": f"chunk_{chunk_idx}",
                    "text": f"[{page_label}]\n{current_chunk.strip()}",
                    "pages": [page_num],
                    "page_labels": [page_label],
                    "is_table": False
                })
                chunk_idx += 1

    return chunks
