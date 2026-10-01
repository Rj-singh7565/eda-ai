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

# ── Performance Optimization Parameters ───────────────────────────────
PARQUET_COMPRESSION = os.getenv("PARQUET_COMPRESSION", "snappy")
DUCKDB_THREADS = int(os.getenv("DUCKDB_THREADS", "0"))  # 0 = auto-detect all cores
SIMILARITY_CACHE_THRESHOLD = float(os.getenv("SIMILARITY_CACHE_THRESHOLD", "0.96"))
SEMANTIC_CACHE_MAX_ENTRIES = int(os.getenv("SEMANTIC_CACHE_MAX_ENTRIES", "500"))
MAX_RAG_CONTEXT_TOKENS = int(os.getenv("MAX_RAG_CONTEXT_TOKENS", "1200"))
PROMPT_MAX_CONTEXT_TOKENS = int(os.getenv("PROMPT_MAX_CONTEXT_TOKENS", "400"))
RAG_TOP_K_CHUNKS = int(os.getenv("RAG_TOP_K_CHUNKS", "5"))
PINECONE_UPSERT_BATCH_SIZE = int(os.getenv("PINECONE_UPSERT_BATCH_SIZE", "250"))

# ── Bounded Concurrency & Semaphores ──────────────────────────────────
EDA_MAX_INGESTION_WORKERS = int(os.getenv("EDA_MAX_INGESTION_WORKERS", "4"))
EDA_MAX_OCR_CONCURRENCY = int(os.getenv("EDA_MAX_OCR_CONCURRENCY", "2"))
EDA_MAX_EMBEDDING_CONCURRENCY = int(os.getenv("EDA_MAX_EMBEDDING_CONCURRENCY", "2"))
EDA_MAX_PINECONE_CONCURRENCY = int(os.getenv("EDA_MAX_PINECONE_CONCURRENCY", "4"))
EDA_MAX_RETRIEVAL_CONCURRENCY = int(os.getenv("EDA_MAX_RETRIEVAL_CONCURRENCY", "4"))
EDA_MAX_DUCKDB_CONCURRENCY = int(os.getenv("EDA_MAX_DUCKDB_CONCURRENCY", "8"))

# ── Database Connection Pooling ───────────────────────────────────────
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

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
