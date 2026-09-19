"""
Backend Configuration — loads environment variables, validates startup requirements, and defines global parameters.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys & Validation ─────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "eda-assistant")

# Database & Storage Configurations
DATABASE_URL = os.getenv("DATABASE_URL")
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local").lower() # 'local', 's3', or 'supabase'
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")

# Frontend & CORS Configurations
FRONTEND_URL = os.getenv("FRONTEND_URL")
CORS_ORIGINS = os.getenv("CORS_ORIGINS")

def validate_config():
    """Verify that mandatory API keys are present."""
    missing = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key":
        missing.append("GROQ_API_KEY")
    if not PINECONE_API_KEY or PINECONE_API_KEY == "your_pinecone_api_key":
        missing.append("PINECONE_API_KEY")
    
    if missing:
        print(f"[WARNING] Missing environment variables: {', '.join(missing)}. Ensure they are set in your .env file or environment.")

# ── Models ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# ── Chunking & Retrieval Parameters ──────────────────────────────────
CHUNK_SIZE = 600       # Target characters per chunk
CHUNK_OVERLAP = 100    # Overlap between chunks
TOP_K = 5              # Number of chunks retrieved per query
SIMILARITY_THRESHOLD = 0.35 # Score threshold below which context is ignored

# ── Constraints & Memory ──────────────────────────────────────────────
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_ZIP_FILES = 15     # Maximum files extracted per ZIP archive
MEMORY_TURNS = 4       # Number of prior Q&A turns to retain per doc session

SUPPORTED_DOC_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"
}
SUPPORTED_EXTENSIONS = SUPPORTED_DOC_EXTENSIONS.union({".zip"})

# ── Paths & Storage ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DB_PATH = os.path.join(BASE_DIR, "eda_assistant.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Run initial validation
validate_config()
