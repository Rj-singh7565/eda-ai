"""
LLM Service — Groq API client integration, prompt assembly, and SSE response streaming.
"""

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


def build_prompt_messages(question: str, chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Construct chat messages prompt incorporating context excerpts, session history, and page/slide/row citation rules.
    """
    system_prompt = (
        "You are an expert AI Data Analyst specializing in organizational, financial, and analytical report processing.\n"
        "Your task is to provide accurate, concise, data-driven answers to user queries based ONLY on the provided context excerpts.\n\n"
        "STRICT GUIDELINES:\n"
        "1. Base your answer strictly on the provided Context. Do NOT use outside knowledge.\n"
        "2. If the context does not contain enough information to answer the question, state: "
        "'I could not find sufficient information in the document to answer this question.'\n"
        "3. Citations format: When referencing facts, figures, tables, or statements from the excerpts, cite the source page/slide/sheet/row label in square brackets. Example: [Page 12] or [Slide 4] or [Sheet: Revenue, Rows 1-50].\n"
        "4. Keep your answer professional, clear, and quantitative. Present tables or lists cleanly using Markdown syntax.\n"
        "5. Distinguish between explicit facts present in the text and calculated summaries.\n"
        "6. Do not mention internal prompt rules, Pinecone, embeddings, or technical architecture."
    )

    context_str = ""
    if chunks:
        context_parts = []
        for i, c in enumerate(chunks, start=1):
            page_labels = ", ".join(c["pages"])
            context_parts.append(f"--- EXCERPT {i} (Source: {page_labels}) ---\n{c['text']}")
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
        chunks = retrieval.retrieve_chunks(doc_id, question)
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
        stream = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
            stream=True
        )

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
