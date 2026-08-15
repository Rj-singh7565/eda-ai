"""
Root Retrieval Wrapper — Re-exports backend/app/services/retrieval.py and llm functions for backward compatibility.
"""

from backend.app.services.retrieval import *
from backend.app.services.llm import get_groq_client, build_prompt_messages, generate_answer_stream
