"""
Documents Router — Status polling, document list, markdown view, and deletion endpoints.
"""

import os
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response

from backend.app import config
from backend.app.database import database
from backend.app.services.storage import storage_service
from backend.app.services import retrieval

router = APIRouter()


@router.get("/documents")
@router.get("/api/documents")
async def list_all_documents():
    """List all registered documents for navigation."""
    return database.list_documents()


@router.get("/stats")
@router.get("/api/stats")
@router.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get aggregated system statistics, storage usage, and activity feed."""
    return database.get_dashboard_stats()


@router.get("/documents/{doc_id}")
@router.get("/api/documents/{doc_id}")
@router.get("/status/{doc_id}")
@router.get("/api/documents/{doc_id}/status")
async def get_document_status(doc_id: str):
    """Poll ingestion status for a document."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("/document/{doc_id}/markdown")
@router.get("/documents/{doc_id}/markdown")
@router.get("/api/documents/{doc_id}/markdown")
async def get_document_markdown(doc_id: str):
    """Retrieve raw normalized Markdown representation for a document."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        md_content = storage_service.read_processed_markdown(doc_id, doc.get("markdown_path"))
        return Response(content=md_content, media_type="text/markdown; charset=utf-8")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Markdown representation not available for this document."
        )


def _purge_pinecone_namespace(doc_id: str):
    try:
        index = retrieval.get_pinecone_index()
        index.delete(delete_all=True, namespace=doc_id)
        print(f"[PINECONE] Successfully deleted all vector chunks in namespace: '{doc_id}'")
    except Exception as e:
        print(f"[WARN] Failed to purge Pinecone namespace '{doc_id}': {e}")


@router.delete("/documents/{doc_id}")
@router.delete("/api/documents/{doc_id}")
async def delete_document_record(doc_id: str, background_tasks: BackgroundTasks):
    """Delete a document, local stored files, and database records instantly; offload Pinecone purge to background."""
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Synchronous database deletion (<1ms)
    database.delete_document(doc_id)

    # Offload storage cleanup to background thread
    background_tasks.add_task(asyncio.to_thread, storage_service.delete_document_files, doc_id)

    # Offload Pinecone purge to background task
    background_tasks.add_task(_purge_pinecone_namespace, doc_id)

    return {"message": f"Document {doc_id} and associated resources deleted successfully."}
