"""
Chat Pydantic Schemas.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionStreamRequest(BaseModel):
    doc_id: str = Field(..., description="Document UUID namespace")
    question: str = Field(..., description="User query text")

class ChatTurn(BaseModel):
    id: Optional[int] = None
    doc_id: str
    question: str
    answer: str
    created_at: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    doc_id: str
    history: List[ChatTurn]
