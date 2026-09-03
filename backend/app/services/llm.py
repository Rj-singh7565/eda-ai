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

def ensure_markdown_table(text: str) -> str:
    """
    Generalized response table wrapper — guarantees that any response text produced for ANY document
    format (structured CSV/Excel, unstructured PDF/DOCX, PPTX, OCR images, TXT, JSON) is formatted strictly as a valid Markdown Table.
    """
    if not text or not text.strip():
        return "| Status | Details |\n| --- | --- |\n| Information Not Found | No data available to format. |"

    clean_text = re.sub(r'<think>[\s\S]*?(?:<\/think>|$)', '', text, flags=re.IGNORECASE).strip()

    # Check if text contains a valid Markdown Table (| Header 1 | Header 2 |)
    lines_with_pipe = [l.strip() for l in clean_text.split("\n") if l.strip().startswith("|")]
    if len(lines_with_pipe) >= 2:
        return clean_text

    # Fallback: Convert key-value pairs or text bullet points into a structured Markdown Table
    raw_lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
    table_rows = []

    for line in raw_lines:
        line_clean = re.sub(r"^[-*•\d+.\s]+", "", line).strip()
        if not line_clean:
            continue
        if ":" in line_clean:
            parts = line_clean.split(":", 1)
            table_rows.append(f"| {parts[0].strip()} | {parts[1].strip()} |")
        elif " - " in line_clean:
            parts = line_clean.split(" - ", 1)
            table_rows.append(f"| {parts[0].strip()} | {parts[1].strip()} |")
        else:
            table_rows.append(f"| Insight / Finding | {line_clean} |")

    if not table_rows:
        return f"| Parameter | Value |\n| --- | --- |\n| Result | {clean_text.replace('|', '/')} |"

    return "| Attribute / Field | Details / Value |\n| --- | --- |\n" + "\n".join(table_rows)


def build_prompt_messages(question: str, chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Construct chat messages prompt incorporating context excerpts, session history, and generalized clean table output rules.
    """
    system_prompt = (
        "You are an expert AI Data Analyst & Document Intelligence Engine for all file types (CSV, Excel, PDF, Word, PPTX, Text, OCR Images, JSON, etc.).\n"
        "Your sole task is to analyze document context excerpts and return answers STRICTLY in Markdown Table format (| Header 1 | Header 2 | ... |).\n\n"
        "UNIVERSAL TABLE OUTPUT GUARANTEE FOR ALL DATA TYPES:\n"
        "1. EXCLUSIVE TABLE FORMAT: Return your response strictly as a Markdown Table. Never output raw paragraphs or prose.\n"
        "2. DYNAMIC & SUFFICIENT HEADERS: Choose logical column headers suited to the question and document type (e.g., '| Feature | Details |', '| Metric | Value | Unit |', '| Entity | Description | Source |', or full dataset columns).\n"
        "3. NO PREAMBLE OR CONVERSATIONAL FILLER: Do NOT include any introductory lines, conversational filler ('Here is the table:'), concluding remarks, or commentary.\n"
        "4. NO INTERNAL METADATA TAGS: Do NOT print internal labels like '[Sheet Data Table]', '[Page 1]', or '[Section General]'. Output ONLY the Markdown Table.\n"
        "5. NO THINKING BLOCKS: Do NOT output <think> tags or chain-of-thought reasoning.\n"
        "6. INSUFFICIENT DATA: If the context does not contain sufficient data, return a single-row Markdown Table:\n"
        "| Status | Details |\n| --- | --- |\n| Information Not Found | I could not find sufficient information in the document to answer this question. |"
    )

    context_str = ""
    if chunks:
        context_parts = []
        for i, c in enumerate(chunks, start=1):
            # Sanitize raw internal bracket tags from excerpt text
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
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "groq/compound",
            "qwen/qwen3.6-27b"
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

        accumulated_raw = ""
        last_yielded_len = 0

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                accumulated_raw += token

                # Strip <think>...</think> reasoning blocks from stream before yielding
                clean_accumulated = re.sub(r'<think>[\s\S]*?(?:<\/think>|$)', '', accumulated_raw, flags=re.IGNORECASE)

                if len(clean_accumulated) > last_yielded_len:
                    new_clean_chunk = clean_accumulated[last_yielded_len:]
                    last_yielded_len = len(clean_accumulated)
                    token_event = {"type": "token", "content": new_clean_chunk}
                    yield f"data: {json.dumps(token_event)}\n\n"

        complete_text = ensure_markdown_table(accumulated_raw)
        database.add_chat_turn(doc_id, question, complete_text)

        done_event = {"type": "done", "status": "completed"}
        yield f"data: {json.dumps(done_event)}\n\n"

    except Exception as e:
        err_msg = f"Error generating answer: {str(e)}"
        print(f"[LLM STREAM ERROR] {err_msg}")
        traceback.print_exc()
        error_event = {"type": "error", "message": err_msg}
        yield f"data: {json.dumps(error_event)}\n\n"
