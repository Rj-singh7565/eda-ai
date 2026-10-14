"""
Analytics Router — Endpoints for Analytical Plans and Reproducible Python Queries.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.database import database
from backend.app.services import dataset_engine, query_router
from backend.app.services.python_query_generator import generate_python_query

import time

router = APIRouter()


class PythonQueryRequest(BaseModel):
    document_id: Optional[str] = None
    doc_id: Optional[str] = None
    query_id: Optional[str] = None
    question: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None


class PythonQueryResponse(BaseModel):
    python_code: str
    language: str = "python"
    library: str = "pandas"
    dataset_name: str
    dataset_version: Optional[str] = None
    operations: List[str]
    is_available: bool = True
    analytical_plan: Optional[Dict[str, Any]] = None
    query_id: Optional[str] = None
    message: Optional[str] = None


@router.post("/api/analytics/python-query", response_model=PythonQueryResponse)
@router.post("/analytics/python-query", response_model=PythonQueryResponse)
async def get_reproducible_python_query(payload: PythonQueryRequest):
    """
    Generate deterministic, reproducible Python (pandas) code for an analytical query or plan.
    Does NOT use LLM hallucination; derives code directly from the canonical analytical plan.
    """
    target_doc_id = (payload.document_id or payload.doc_id or "").strip()
    if not target_doc_id:
        raise HTTPException(status_code=400, detail="Missing document_id or doc_id.")

    doc = database.get_document(target_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{target_doc_id}' not found.")

    dataset_name = doc.get("filename") or f"{target_doc_id}.parquet"
    version_str = doc.get("updated_at") or doc.get("created_at") or "v1.0"
    query_id = payload.query_id or f"q_{int(time.time() * 1000)}"

    plan = payload.plan
    if not plan and payload.question:
        schema_info = dataset_engine.get_dataset_schema(target_doc_id)
        if "error" in schema_info:
            raise HTTPException(status_code=400, detail=schema_info["error"])

        prev_plan = None
        recent_turns = database.get_recent_chat_history(target_doc_id, limit=1)
        if recent_turns and len(recent_turns) > 0:
            prev_q = recent_turns[0].get("question", "")
            if prev_q:
                prev_plan = query_router.plan_structured_operation(prev_q, schema_info)

        plan = query_router.plan_structured_operation(payload.question, schema_info, prev_plan=prev_plan)

    if not plan:
        # Default to standard selection if no query/plan was sent
        plan = {
            "operation": "select",
            "target_columns": [],
            "preserve_all_columns": True,
            "conditions": [],
            "sort_by": [],
            "group_by": [],
            "aggregations": [],
            "limit": 100
        }

    generated = generate_python_query(plan, dataset_name=dataset_name, sheet_name=plan.get("sheet_name"))

    return PythonQueryResponse(
        python_code=generated["python_code"],
        language=generated.get("language", "python"),
        library=generated.get("library", "pandas"),
        dataset_name=generated.get("dataset_name", dataset_name),
        dataset_version=version_str,
        operations=generated.get("operations", ["select"]),
        is_available=generated.get("is_available", True),
        analytical_plan=plan,
        query_id=query_id,
        message=generated.get("message", "Generated reproducible Python code.")
    )
