"""
Data Models for Document Registry and Chat History.
"""

from typing import Optional, Dict, Any

class DocumentModel:
    def __init__(
        self,
        doc_id: str,
        filename: str,
        file_size: int,
        file_type: str = "pdf",
        page_count: int = 0,
        chunk_count: int = 0,
        status: str = "processing",
        error_message: Optional[str] = None,
        markdown_path: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        self.doc_id = doc_id
        self.filename = filename
        self.file_size = file_size
        self.file_type = file_type
        self.page_count = page_count
        self.chunk_count = chunk_count
        self.status = status
        self.error_message = error_message
        self.markdown_path = markdown_path
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "error_message": self.error_message,
            "markdown_path": self.markdown_path,
            "created_at": str(self.created_at) if self.created_at else None
        }
