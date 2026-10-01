"""
LLM Service — Hybrid Query Router integration, Deterministic DuckDB/DataFrame execution,
StreamingThinkFilter state machine, structured SSE events, and sub-second table_ready emission.
"""

import asyncio
import json
import re
import time
import traceback
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from groq import Groq
from fastapi import Request

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


def format_sse(event_name: str, data: Dict[str, Any]) -> str:
    """Format SSE frame compatible with standard event listeners and legacy data-payload consumers."""
    if "type" not in data:
        data["type"] = event_name
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


class StreamingThinkFilter:
    """
    High-performance streaming state machine that filters <think>...</think> reasoning tags
    across arbitrary chunk boundaries without regex re-scans or memory bloat.
    """
    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self):
        self.in_think = False
        self.buffer = ""

    def process_token(self, token: str) -> str:
        """Process incoming token and return sanitized display text."""
        if not token:
            return ""
        output = []
        for char in token:
            if not self.in_think:
                test_buf = self.buffer + char
                test_buf_lower = test_buf.lower()
                if test_buf_lower == self.OPEN_TAG:
                    self.in_think = True
                    self.buffer = ""
                elif self.OPEN_TAG.startswith(test_buf_lower):
                    self.buffer = test_buf
                else:
                    found_prefix = False
                    for i in range(1, len(test_buf)):
                        suffix = test_buf[i:]
                        if self.OPEN_TAG.startswith(suffix.lower()):
                            output.append(test_buf[:i])
                            self.buffer = suffix
                            found_prefix = True
                            break
                    if not found_prefix:
                        output.append(test_buf)
                        self.buffer = ""
            else:
                test_buf = self.buffer + char
                test_buf_lower = test_buf.lower()
                if test_buf_lower == self.CLOSE_TAG:
                    self.in_think = False
                    self.buffer = ""
                elif self.CLOSE_TAG.startswith(test_buf_lower):
                    self.buffer = test_buf
                else:
                    found_prefix = False
                    for i in range(1, len(test_buf)):
                        suffix = test_buf[i:]
                        if self.CLOSE_TAG.startswith(suffix.lower()):
                            self.buffer = suffix
                            found_prefix = True
                            break
                    if not found_prefix:
                        self.buffer = ""
        return "".join(output)

    def flush(self) -> str:
        """Flush any pending characters at end of stream if outside thinking block."""
        if not self.in_think and self.buffer:
            out = self.buffer
            self.buffer = ""
            return out
        self.buffer = ""
        return ""


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
    Build prompt for unstructured document Q&A with evidence grounding and bounded token budget.
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

    # Budget context: ~4 chars per token, max config.MAX_RAG_CONTEXT_TOKENS
    max_chars = config.MAX_RAG_CONTEXT_TOKENS * 4
    context_parts = []
    current_chars = 0

    if chunks:
        for i, c in enumerate(chunks[:5], start=1):
            raw_text = c.get("text", "").strip()
            clean_text = re.sub(r"^\[(Sheet|Page|Slide|Section|Row|Rows)[^\]]*\]\n?", "", raw_text, flags=re.IGNORECASE).strip()
            page_labels = ", ".join(c.get("pages", []))
            part = f"--- EXCERPT {i} (Source: {page_labels}) ---\n{clean_text}"
            if current_chars + len(part) > max_chars and context_parts:
                break
            context_parts.append(part)
            current_chars += len(part)
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


async def generate_answer_stream(
    doc_id: str,
    question: str,
    request: Optional[Request] = None
) -> AsyncGenerator[str, None]:
    """
    Stream answer tokens token-by-token using Server-Sent Events (SSE).
    Dynamically routes between Deterministic DataFrame/DuckDB Engine and Adaptive Document RAG.
    Supports request cancellation, instant table_ready emission, and streaming think filter.
    """
    start_time = time.time()
    try:
        # Check cancellation
        if request and await request.is_disconnected():
            logger.info(f"[CLIENT DISCONNECT] Aborting stream for doc_id={doc_id} before routing.")
            return

        # Step 1: Fast Query Classification & Routing (<5ms with DB metadata)
        query_type, schema_info = query_router.classify_query(question, doc_id)
        router_latency_ms = (time.time() - start_time) * 1000.0
        logger.info(f"[QUERY ROUTER] doc_id={doc_id} query='{question[:40]}' classified_as={query_type} in {router_latency_ms:.1f}ms")

        # ── BRANCH A: STRUCTURED DATASET OPERATION (DUCKDB / PARQUET) ────────
        if query_type == "STRUCTURED_DATA_OPERATION" and schema_info:
            plan = query_router.plan_structured_operation(question, schema_info)
            df_result = dataset_engine.execute_dataframe_operation(doc_id, plan)

            # Handle Schema / Missing Column Errors Gracefully
            if not df_result.get("success"):
                err_msg = df_result.get("message", "Error executing dataset query.")
                yield format_sse("metadata", {"citations": [], "has_context": False})
                yield format_sse("token", {"content": err_msg})
                database.add_chat_turn(doc_id, question, err_msg)
                yield format_sse("done", {"status": "completed"})
                return

            md_table = df_result.get("markdown_table", "")
            sql_query = df_result.get("sql_query", plan.get("sql", "SELECT * FROM active_dataset LIMIT 10;"))
            exec_latency_ms = df_result.get("execution_latency_ms", (time.time() - start_time) * 1000.0)

            # Build Citation for Structured Dataset
            sheet_label = plan.get("sheet_name") or "Dataset"
            total_rows = df_result.get("total_dataset_rows", 0)
            res_rows_count = df_result.get("row_count", 0)
            cols_count = len(df_result.get("columns", []))

            citations = [{
                "pages": [f"{sheet_label} ({res_rows_count} / {total_rows} rows)"],
                "score": 1.0,
                "text_snippet": f"Executed deterministic {plan.get('operation')} operation. Returned {res_rows_count} rows across {cols_count} columns.",
                "full_text": md_table,
                "is_table": True
            }]

            # 1. EMIT table_ready EVENT IMMEDIATELY (Sub-Second Target)
            table_ready_payload = {
                "type": "table_ready",
                "table_markdown": md_table,
                "sql_query": sql_query,
                "latency_ms": round(exec_latency_ms, 2),
                "row_count": res_rows_count,
                "column_count": cols_count
            }
            yield format_sse("table_ready", table_ready_payload)

            # 2. EMIT metadata EVENT (Citations & Schema Context)
            yield format_sse("metadata", {"citations": citations, "has_context": True})
            yield format_sse("citation", {"citations": citations})

            # 3. Stream Markdown Table as primary token for legacy consumers
            yield format_sse("token", {"content": md_table})

            # Check client disconnection before generating executive insight
            if request and await request.is_disconnected():
                logger.info("[CLIENT DISCONNECT] Client disconnected before insight generation.")
                database.add_chat_turn(doc_id, question, md_table)
                return

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
            think_filter = StreamingThinkFilter()
            try:
                for model_name in unique_models:
                    if request and await request.is_disconnected():
                        break
                    try:
                        stream = client.chat.completions.create(
                            model=model_name,
                            messages=insight_prompt,
                            temperature=0.2,
                            max_tokens=250,
                            stream=True
                        )
                        # Stream insight prefix
                        yield format_sse("token", {"content": "\n\n**Insight:** "})
                        for chunk in stream:
                            if request and await request.is_disconnected():
                                logger.info("[CLIENT DISCONNECT] Disconnected during tabular insight stream.")
                                break
                            if chunk.choices and chunk.choices[0].delta.content:
                                tok = chunk.choices[0].delta.content
                                clean_tok = think_filter.process_token(tok)
                                if clean_tok:
                                    insight_text += clean_tok
                                    yield format_sse("token", {"content": clean_tok})
                        flushed = think_filter.flush()
                        if flushed:
                            insight_text += flushed
                            yield format_sse("token", {"content": flushed})
                        break
                    except Exception as model_err:
                        logger.warning(f"Groq insight model '{model_name}' note: {model_err}")
            except Exception as e:
                logger.warning(f"Insight generation skipped: {e}")

            # Persist complete response to database
            full_answer = md_table
            if insight_text.strip():
                full_answer += f"\n\n**Insight:** {insight_text.strip()}"
            database.add_chat_turn(doc_id, question, full_answer)

            total_elapsed = (time.time() - start_time) * 1000.0
            yield format_sse("done", {"status": "completed", "total_latency_ms": round(total_elapsed, 2)})
            return

        # ── BRANCH B: ADAPTIVE DOCUMENT RAG ───────────────────────────────────
        chunks = await asyncio.to_thread(retrieval.retrieve_chunks, doc_id, question)

        if request and await request.is_disconnected():
            logger.info("[CLIENT DISCONNECT] Disconnected after document retrieval.")
            return

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

        yield format_sse("metadata", {"citations": citations, "has_context": len(chunks) > 0})
        yield format_sse("citation", {"citations": citations})

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
            if request and await request.is_disconnected():
                return
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

        think_filter = StreamingThinkFilter()
        accumulated_clean = ""
        ttft_recorded = False

        for chunk in stream:
            if request and await request.is_disconnected():
                logger.info("[CLIENT DISCONNECT] Client disconnected during RAG generation.")
                break
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                clean_tok = think_filter.process_token(token)
                if clean_tok:
                    if not ttft_recorded:
                        ttft_ms = (time.time() - start_time) * 1000.0
                        logger.info(f"[LLM TTFT] Time to first token: {ttft_ms:.1f}ms for doc_id={doc_id}")
                        ttft_recorded = True
                    accumulated_clean += clean_tok
                    yield format_sse("token", {"content": clean_tok})

        flushed = think_filter.flush()
        if flushed:
            accumulated_clean += flushed
            yield format_sse("token", {"content": flushed})

        database.add_chat_turn(doc_id, question, accumulated_clean.strip())
        total_elapsed = (time.time() - start_time) * 1000.0
        yield format_sse("done", {"status": "completed", "total_latency_ms": round(total_elapsed, 2)})

    except Exception as e:
        err_msg = f"Error generating answer: {str(e)}"
        logger.error(f"[LLM STREAM ERROR] {err_msg}")
        traceback.print_exc()
        yield format_sse("error", {"message": "An error occurred while generating the answer. Please try again."})
