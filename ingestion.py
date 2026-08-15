"""
Root Ingestion Wrapper — Re-exports backend/app/services/ingestion.py and extraction functions for backward compatibility.
"""

from backend.app.services.ingestion import *
from backend.app.services.extraction import *
from backend.app.services.normalization import normalize_to_markdown
from backend.app.services.chunking import chunk_markdown, chunk_text_sentence_aware
from backend.app.services.embeddings import get_embedding_model
