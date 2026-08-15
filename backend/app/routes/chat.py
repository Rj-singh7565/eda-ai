"""
Chat Router — SSE stream Q&A endpoint and chat session history.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.schemas.chat import QuestionStreamRequest
from backend.app.database import database
from backend.app.services import llm

router = APIRouter()


@router.post("/ask/stream")
@router.post("/api/chat/stream")
async def ask_question_stream(request: Request, payload: QuestionStreamRequest):
    """
    Accept a natural language question and stream the response via Server-Sent Events (SSE).
    """
    doc_id = payload.doc_id.strip()
    question = payload.question.strip()

    if not doc_id:
        raise HTTPException(status_code=400, detail="Missing doc_id parameter.")

    if not question:
        raise HTTPException(status_code=400, detail="Please provide a question.")

    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready yet. Current status: {doc['status']}"
        )

    return StreamingResponse(
        llm.generate_answer_stream(doc_id, question),
        media_type="text/event-stream"
    )


@router.get("/documents/{doc_id}/history")
@router.get("/api/chat/{doc_id}/history")
async def get_document_chat_history(doc_id: str):
    """Retrieve chat history session for a document."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    history = database.get_recent_chat_history(doc_id, limit=20)
    return {"doc_id": doc_id, "history": history}
