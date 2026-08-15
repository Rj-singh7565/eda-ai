"""
Document Pydantic Schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_size: int
    file_type: str
    page_count: int = 0
    chunk_count: int = 0
    status: str
    error_message: Optional[str] = None
    markdown_path: Optional[str] = None
    created_at: Optional[str] = None

class SkippedFile(BaseModel):
    filename: str
    reason: str

class UploadResponse(BaseModel):
    batch: bool
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    status: str = "processing"
    documents: List[DocumentResponse] = []
    skipped: List[SkippedFile] = []
    message: str
