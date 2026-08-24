"""
LLM Service — Groq API client integration, prompt assembly, and SSE response streaming.
"""

import asyncio
import json
import traceback
from typing import List, Dict, Any, AsyncGenerator
from groq import Groq

from backend.app import config
from backend.app.database import database
from backend.app.services import retrieval

_groq_client = None


def get_groq_client() -> Groq:
    """Lazy initialization of Groq API client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


import re

def build_prompt_messages(question: str, chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Construct chat messages prompt incorporating context excerpts, session history, and clean table output rules.
    """
    system_prompt = (
        "You are an expert AI Data Analyst specializing in document intelligence and exploratory data analysis.\n"
        "Your task is to provide accurate, concise, data-driven answers strictly in clean Markdown Table format based on the provided context excerpts.\n\n"
        "STRICT OUTPUT FORMAT & CLEANLINESS RULES:\n"
        "1. EXCLUSIVE TABLE FORMAT: Provide ONLY the direct, sufficient answer formatted strictly as a Markdown Table (| Header 1 | Header 2 |).\n"
        "2. NO PREAMBLE OR CONVERSATIONAL FILLER: Do NOT include any introductory sentences, conversational filler ('Here is the table:', 'Based on the document...'), concluding notes, or extra commentary.\n"
        "3. NO INTERNAL LABELS: Do NOT print internal metadata labels, sheet markers, or raw chunk tags like '[Sheet 'Data' (Rows 1-39) Table]', '[Page 1 Table]', or '[Section General]'. Output ONLY the clean table.\n"
        "4. SUFFICIENT DATA ONLY: Output only the exact rows and columns needed to directly answer the user's question.\n"
        "5. INSUFFICIENT DATA: If the context does not contain sufficient data to answer the query, return a single-row Markdown Table with the message:\n"
        "| Status | Details |\n| --- | --- |\n| Information Not Found | I could not find sufficient information in the document to answer this question. |"
    )

    context_str = ""
    if chunks:
        context_parts = []
        for i, c in enumerate(chunks, start=1):
            # Sanitize raw internal bracket tags like [Sheet 'Data' (Rows 1-39) Table] from excerpt text
            raw_text = c.get("text", "")
            clean_text = re.sub(r"^\[(Sheet|Page|Slide|Section|Row|Rows)[^\]]*\]\n?", "", raw_text, flags=re.IGNORECASE).strip()
            page_labels = ", ".join(c.get("pages", []))
            context_parts.append(f"--- EXCERPT {i} (Source: {page_labels}) ---\n{clean_text}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "NO RELEVANT CONTEXT FOUND (All vector search matches fell below confidence similarity threshold)."

    messages = [{"role": "system", "content": system_prompt}]

    # Append short-term conversation memory turns
    for turn in chat_history:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    user_payload = f"DOCUMENT CONTEXT EXCERPTS:\n{context_str}\n\nUSER QUESTION: {question}"
    messages.append({"role": "user", "content": user_payload})

    return messages


async def generate_answer_stream(doc_id: str, question: str) -> AsyncGenerator[str, None]:
    """
    Stream answer tokens token-by-token using Server-Sent Events (SSE).
    First yields metadata (citations & confidence scores), then content tokens, then done signal.
    """
    try:
        # Offload CPU embedding and Pinecone vector query to worker thread to avoid blocking loop
        chunks = await asyncio.to_thread(retrieval.retrieve_chunks, doc_id, question)
        history = database.get_recent_chat_history(doc_id, limit=config.MEMORY_TURNS)
        messages = build_prompt_messages(question, chunks, history)

        # Build citation cards payload
        citations = []
        for c in chunks:
            citations.append({
                "pages": c["pages"],
                "score": c["score"],
                "text_snippet": c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
                "full_text": c["text"],
                "is_table": c.get("is_table", False)
            })

        metadata_event = {
            "type": "metadata",
            "citations": citations,
            "has_context": len(chunks) > 0
        }
        yield f"data: {json.dumps(metadata_event)}\n\n"

        client = get_groq_client()
        candidate_models = [
            config.LLM_MODEL,
            "groq/compound-mini",
            "groq/compound",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile"
        ]

        # Deduplicate candidates while preserving order
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
                print(f"[LLM] Model '{model_name}' failed: {ex}. Trying next fallback...")

        if stream is None:
            raise last_exception or Exception("All candidate LLM models failed on Groq API.")

        full_answer = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_answer.append(token)
                token_event = {"type": "token", "content": token}
                yield f"data: {json.dumps(token_event)}\n\n"

        complete_text = "".join(full_answer)
        database.add_chat_turn(doc_id, question, complete_text)

        done_event = {"type": "done", "status": "completed"}
        yield f"data: {json.dumps(done_event)}\n\n"

    except Exception as e:
        err_msg = f"Error generating answer: {str(e)}"
        print(f"[LLM STREAM ERROR] {err_msg}")
        traceback.print_exc()
        error_event = {"type": "error", "message": err_msg}
        yield f"data: {json.dumps(error_event)}\n\n"
