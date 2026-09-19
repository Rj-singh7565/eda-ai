"""
LLM Service — Hybrid Query Router integration, Deterministic DataFrame execution,
and SSE response streaming with Citations and Executive Insights.
"""

import asyncio
import json
import re
import traceback
import logging
from typing import List, Dict, Any, AsyncGenerator
from groq import Groq

from backend.app import config
from backend.app.database import database
from backend.app.services import retrieval, dataset_engine, query_router

logger = logging.getLogger("eda.llm")
_groq_client = None


def get_groq_client() -> Groq:
    """Lazy initialization of Groq API client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def build_insight_prompt(question: str, df_summary_msg: str, table_snippet: str) -> List[Dict[str, str]]:
    """
    Build prompt for generating concise analytical insights on verified DataFrame results.
    """
    system_prompt = (
        "You are an expert AI Data Analyst. A deterministic DataFrame operation has computed the exact table data.\n"
        "Your task is to provide a concise, sharp 1 to 2 sentence executive insight or summary of the findings.\n"
        "RULES:\n"
        "1. Do NOT repeat or recreate the table — it is already displayed.\n"
        "2. Do NOT contradict or alter the computed values.\n"
        "3. Focus on key takeaways, patterns, highest/lowest metrics, or totals.\n"
        "4. Be direct, professional, and clear."
    )

    user_prompt = (
        f"USER QUESTION: {question}\n\n"
        f"COMPUTED RESULT SUMMARY: {df_summary_msg}\n\n"
        f"RESULT DATA EXCERPT:\n{table_snippet}\n\n"
        "Provide a 1-2 sentence executive insight:"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def build_document_rag_prompt(
    question: str,
    chunks: List[Dict[str, Any]],
    chat_history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Build prompt for unstructured document Q&A with evidence grounding.
    """
    system_prompt = (
        "You are an expert AI Document Intelligence Analyst.\n"
        "Analyze the provided document excerpts and answer the user's question accurately.\n"
        "RULES:\n"
        "1. Answer ONLY based on the provided document excerpts.\n"
        "2. If the excerpts do NOT contain sufficient information to answer the question, clearly state:\n"
        "   'I could not find sufficient information in the document to answer this question.'\n"
        "3. Maintain high precision and cite specific sections or page references where applicable.\n"
        "4. Use clear Markdown formatting with tables or bullet points when structured data is described."
    )

    context_parts = []
    if chunks:
        for i, c in enumerate(chunks, start=1):
            raw_text = c.get("text", "").strip()
            clean_text = re.sub(r"^\[(Sheet|Page|Slide|Section|Row|Rows)[^\]]*\]\n?", "", raw_text, flags=re.IGNORECASE).strip()
            page_labels = ", ".join(c.get("pages", []))
            context_parts.append(f"--- EXCERPT {i} (Source: {page_labels}) ---\n{clean_text}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "NO RELEVANT EXCERPTS FOUND."

    messages = [{"role": "system", "content": system_prompt}]

    # Append recent memory turns
    for turn in chat_history:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    user_payload = f"DOCUMENT EXCERPTS:\n{context_str}\n\nUSER QUESTION: {question}"
    messages.append({"role": "user", "content": user_payload})

    return messages


async def generate_answer_stream(doc_id: str, question: str) -> AsyncGenerator[str, None]:
    """
    Stream answer tokens token-by-token using Server-Sent Events (SSE).
    Dynamically routes between Deterministic DataFrame Engine and Adaptive Document RAG.
    """
    try:
        # Step 1: Query Classification & Routing
        query_type, schema_info = query_router.classify_query(question, doc_id)
        logger.info(f"[QUERY ROUTER] doc_id={doc_id} query='{question[:40]}' classified_as={query_type}")

        # ── BRANCH A: STRUCTURED DATASET OPERATION ────────────────────────────
        if query_type == "STRUCTURED_DATA_OPERATION" and schema_info:
            plan = query_router.plan_structured_operation(question, schema_info)
            df_result = dataset_engine.execute_dataframe_operation(doc_id, plan)

            # Handle Schema / Missing Column Errors Gracefully
            if not df_result.get("success"):
                err_msg = df_result.get("message", "Error executing dataset query.")
                # Send metadata with empty citations
                yield f"data: {json.dumps({'type': 'metadata', 'citations': [], 'has_context': False})}\n\n"
                # Stream the schema-aware message
                yield f"data: {json.dumps({'type': 'token', 'content': err_msg})}\n\n"
                database.add_chat_turn(doc_id, question, err_msg)
                yield f"data: {json.dumps({'type': 'done', 'status': 'completed'})}\n\n"
                return

            # Build Citation for Structured Dataset
            sheet_label = plan.get("sheet_name") or "Dataset"
            total_rows = df_result.get("total_dataset_rows", 0)
            res_rows_count = df_result.get("row_count", 0)
            cols_count = len(df_result.get("columns", []))

            citations = [{
                "pages": [f"{sheet_label} ({res_rows_count} / {total_rows} rows)"],
                "score": 1.0,
                "text_snippet": f"Executed deterministic {plan.get('operation')} operation. Returned {res_rows_count} rows across {cols_count} columns.",
                "full_text": df_result.get("markdown_table", ""),
                "is_table": True
            }]

            yield f"data: {json.dumps({'type': 'metadata', 'citations': citations, 'has_context': True})}\n\n"

            # Stream the pristine Markdown Table directly from the verified DataFrame
            md_table = df_result.get("markdown_table", "")
            # Yield table in responsive chunks
            yield f"data: {json.dumps({'type': 'token', 'content': md_table})}\n\n"

            # Generate AI Executive Insight over the verified result
            table_snippet = md_table[:1000]
            insight_prompt = build_insight_prompt(question, df_result.get("message", ""), table_snippet)

            client = get_groq_client()
            candidate_models = [
                config.LLM_MODEL,
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768"
            ]

            unique_models = []
            for m in candidate_models:
                if m and m not in unique_models:
                    unique_models.append(m)

            insight_text = ""
            try:
                for model_name in unique_models:
                    try:
                        stream = client.chat.completions.create(
                            model=model_name,
                            messages=insight_prompt,
                            temperature=0.2,
                            max_tokens=250,
                            stream=True
                        )
                        # Stream insight prefix
                        yield f"data: {json.dumps({'type': 'token', 'content': '\n\n**Insight:** '})}\n\n"
                        for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                tok = chunk.choices[0].delta.content
                                insight_text += tok
                                yield f"data: {json.dumps({'type': 'token', 'content': tok})}\n\n"
                        break
                    except Exception as model_err:
                        logger.warning(f"Groq insight model '{model_name}' note: {model_err}")
            except Exception as e:
                logger.warning(f"Insight generation skipped: {e}")

            # Persist the complete response to database
            full_answer = md_table
            if insight_text.strip():
                full_answer += f"\n\n**Insight:** {insight_text.strip()}"
            database.add_chat_turn(doc_id, question, full_answer)

            yield f"data: {json.dumps({'type': 'done', 'status': 'completed'})}\n\n"
            return

        # ── BRANCH B: ADAPTIVE DOCUMENT RAG ───────────────────────────────────
        chunks = await asyncio.to_thread(retrieval.retrieve_chunks, doc_id, question)
        history = database.get_recent_chat_history(doc_id, limit=config.MEMORY_TURNS)
        messages = build_document_rag_prompt(question, chunks, history)

        citations = []
        for c in chunks:
            citations.append({
                "pages": c.get("pages", []),
                "score": c.get("score", 0.8),
                "text_snippet": c.get("text", "")[:300] + ("..." if len(c.get("text", "")) > 300 else ""),
                "full_text": c.get("text", ""),
                "is_table": c.get("is_table", False)
            })

        yield f"data: {json.dumps({'type': 'metadata', 'citations': citations, 'has_context': len(chunks) > 0})}\n\n"

        client = get_groq_client()
        candidate_models = [
            config.LLM_MODEL,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]

        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        stream = None
        last_exception = None
        for model_name in unique_models:
            try:
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1500,
                    stream=True
                )
                break
            except Exception as ex:
                last_exception = ex
                logger.warning(f"Groq RAG model '{model_name}' failed: {ex}. Trying next candidate...")

        if stream is None:
            raise last_exception or Exception("All candidate LLM models failed on Groq API.")

        accumulated_raw = ""
        last_yielded_len = 0

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                accumulated_raw += token

                clean_accumulated = re.sub(r'<think>[\s\S]*?(?:<\/think>|$)', '', accumulated_raw, flags=re.IGNORECASE)

                if len(clean_accumulated) > last_yielded_len:
                    new_clean_chunk = clean_accumulated[last_yielded_len:]
                    last_yielded_len = len(clean_accumulated)
                    yield f"data: {json.dumps({'type': 'token', 'content': new_clean_chunk})}\n\n"

        database.add_chat_turn(doc_id, question, accumulated_raw.strip())
        yield f"data: {json.dumps({'type': 'done', 'status': 'completed'})}\n\n"

    except Exception as e:
        err_msg = f"Error generating answer: {str(e)}"
        logger.error(f"[LLM STREAM ERROR] {err_msg}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'message': err_msg})}\n\n"
