"""
Normalization Service — Converts extracted document structure into canonical Markdown with YAML frontmatter.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union


def normalize_to_markdown(
    arg1: Union[List[Dict[str, Any]], str],
    arg2: str = "pdf",
    arg3: str = "document",
    arg4: str = "doc_id"
) -> str:
    """
    Generate canonical Markdown representation with YAML front matter header.
    Supports flexible signature for backward compatibility with existing tests:
    - (pages_data, file_type, original_filename, doc_id)
    - (doc_id, original_filename, file_type, pages_data)
    """
    if isinstance(arg1, list):
        pages_data = arg1
        file_type = str(arg2)
        original_filename = str(arg3)
        doc_id = str(arg4)
    else:
        doc_id = str(arg1)
        original_filename = str(arg2)
        file_type = str(arg3)
        pages_data = arg4 if isinstance(arg4, list) else []

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    page_count = len(pages_data)

    front_matter = [
        "---",
        f"title: {original_filename}",
        f"source_filename: {original_filename}",
        f"file_type: {file_type}",
        f"doc_id: {doc_id}",
        f"ingested_at: {now_iso}"
    ]

    if file_type == "pptx":
        front_matter.append(f"slide_count: {page_count}")
    elif file_type == "csv":
        # Estimate row count from tables or items
        total_rows = 0
        for item in pages_data:
            for tbl in item.get("tables", []):
                lines = [l for l in tbl.splitlines() if l.startswith("|")]
                if len(lines) > 2:
                    total_rows += len(lines) - 2
        front_matter.append(f"row_count: {total_rows if total_rows > 0 else page_count}")
    else:
        front_matter.append(f"page_count: {page_count}")

    front_matter.extend(["---", ""])

    body = []
    for item in pages_data:
        label = item.get("page_label", f"Page {item.get('page', 1)}")
        if file_type == "image":
            header_str = "## Extracted Text (OCR)"
        elif label.startswith("## "):
            header_str = label
        elif label.startswith("# "):
            header_str = f"#{label}"
        else:
            header_str = f"## {label}"

        body.append(f"{header_str}\n")

        text = item.get("text", "").strip()
        tables = item.get("tables", [])

        if text:
            body.append(f"{text}\n")

        if tables:
            for tbl in tables:
                if tbl and tbl not in text:
                    body.append(f"{tbl}\n")

        body.append("\n---\n")

    return "\n".join(front_matter) + "\n" + "\n".join(body)
