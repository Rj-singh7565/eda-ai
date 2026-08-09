"""
FastAPI Backend — Async upload pipeline, status polling, document registry, SSE answer streaming, and rate limiting.
"""

import os
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import config
import database
import ingestion
import retrieval

# ── App & Rate Limiter Setup ──────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="AI-Based EDA Assistant", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Request Models ────────────────────────────────────────────────────

class QuestionStreamRequest(BaseModel):
    doc_id: str = Field(..., description="Document UUID namespace")
    question: str = Field(..., description="User query text")

# ── Routes ────────────────────────────────────────────────────────────

@app.get("/")
async def home(request: Request):
    """Serve the split-pane frontend workspace."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
@limiter.limit("10/minute")
async def upload_pdf(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a PDF document.
    Validates file, registers metadata, returns doc_id immediately, and processes asynchronously in background.
    """
    # 1. Validate extension
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid file type. Only PDF documents (.pdf) are supported."}
        )

    # 2. Read contents & validate file size / magic header
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        return JSONResponse(
            status_code=400,
            content={"message": "Uploaded file is empty."}
        )

    if file_size > config.MAX_FILE_SIZE_BYTES:
        return JSONResponse(
            status_code=400,
            content={"message": f"File size exceeds limit of {config.MAX_FILE_SIZE_MB}MB."}
        )

    # Magic byte check for PDF (%PDF-)
    if not contents.startswith(b"%PDF-"):
        return JSONResponse(
            status_code=400,
            content={"message": "Corrupted or invalid PDF document format."}
        )

    # 3. Create unique doc_id & save file
    doc_id = str(uuid.uuid4())
    save_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")

    try:
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Failed to save uploaded file: {str(e)}"}
        )

    # 4. Register in SQLite database
    doc_record = database.create_document(doc_id, filename, file_size)

    # 5. Dispatch background ingestion pipeline
    background_tasks.add_task(ingestion.run_ingestion_pipeline, doc_id, save_path)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "status": "processing",
        "message": "Upload successful. Document ingestion initiated."
    }


@app.get("/status/{doc_id}")
async def get_document_status(doc_id: str):
    """Poll ingestion status for a document."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@app.get("/documents")
async def list_all_documents():
    """List all registered documents for sidebar navigation."""
    return database.list_documents()


@app.get("/documents/{doc_id}/history")
async def get_document_chat_history(doc_id: str):
    """Retrieve chat history session for a document."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    history = database.get_recent_chat_history(doc_id, limit=20)
    return {"doc_id": doc_id, "history": history}


@app.delete("/documents/{doc_id}")
async def delete_document_record(doc_id: str):
    """Delete a document, its Pinecone namespace, local PDF file, and database records."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove local file
    save_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
        except Exception:
            pass

    # Purge Pinecone namespace
    try:
        index = retrieval.get_pinecone_index()
        index.delete(delete_all=True, namespace=doc_id)
    except Exception as e:
        print(f"[WARN] Failed to purge Pinecone namespace {doc_id}: {e}")

    # Delete SQLite records
    database.delete_document(doc_id)

    return {"message": f"Document {doc_id} and associated resources deleted successfully."}


@app.post("/ask/stream")
@limiter.limit("20/minute")
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

    # Verify document exists and is ready
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready yet. Current status: {doc['status']}"
        )

    return StreamingResponse(
        retrieval.generate_answer_stream(doc_id, question),
        media_type="text/event-stream"
    )
