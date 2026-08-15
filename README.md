# AI-Based EDA Assistant — Production-Ready MVP

An enterprise-grade Retrieval-Augmented Generation (RAG) system for data-heavy document intelligence, exploratory data analysis, and natural-language document Q&A with verifiable page/slide/row citations.

---

## 1. System Architecture

```text
                    USER
                      |
                      v
             +----------------+
             | Next.js Frontend|  (Vercel)
             +-------+---------+
                     |
                  HTTPS API
                     |
                     v
             +----------------+
             | FastAPI Backend|  (Docker on Render / Railway)
             +-------+--------+
                     |
        +------------+------------+
        |            |            |
        v            v            v
   PostgreSQL    Pinecone      Object Storage
   (Supabase)    (Vectors)     (S3 / Supabase)
        |            |
        |            v
        |          RAG
        |            |
        |            v
        |         Groq API
        |       Llama 3.3 70B
```

---

## 2. Tech Stack

* **Frontend**: Next.js 14, React 18, TypeScript, Lucide Icons, Vanilla CSS Custom Variables Design System (`AGENTS.md` compliant).
* **Backend**: FastAPI (Python 3.12+), Uvicorn, SlowAPI rate limiting, Tenacity retry protection.
* **Database**: PostgreSQL (Supabase / Neon) for cloud production, SQLite (`eda_assistant.db`) fallback for local zero-config dev.
* **Storage**: Abstracted Object Storage (AWS S3 / Supabase Storage) with local file fallback (`uploads/`, `processed/`).
* **Vector Database**: Pinecone Serverless Index with document-level namespace isolation (`namespace=doc_id`).
* **Embeddings**: SentenceTransformers (`BAAI/bge-small-en-v1.5`, 384-dimensional).
* **LLM Engine**: Groq API (`llama-3.3-70b-versatile`) with token-by-token SSE streaming.
* **Document Extraction**: `pypdf`, `pdfplumber`, `python-docx`, `python-pptx`, `pandas`, `openpyxl`, `pytesseract` OCR.

---

## 3. Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in required values:

```env
# Mandatory LLM & Vector DB Keys
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=eda-assistant

# Production PostgreSQL Database (Optional - Defaults to local SQLite if omitted)
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres

# Production Object Storage (Optional - Defaults to local filesystem if omitted)
STORAGE_TYPE=local # 'local', 's3', or 'supabase'
S3_BUCKET=your_s3_bucket
S3_ENDPOINT_URL=https://s3.amazonaws.com
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

---

## 4. Local Quick Start

### Option A: Python Local Virtual Environment

1. Activate virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS / Linux
   pip install -r requirements.txt
   ```

2. Run the test suite:
   ```bash
   python -m pytest
   ```

3. Launch backend server:
   ```bash
   uvicorn app:app --reload --port 8000
   ```
   Open browser at: `http://localhost:8000`

### Option B: Docker Compose

```bash
docker-compose up --build
```
Access backend at `http://localhost:8000`.

---

## 5. Production Cloud Deployment

### 1. Database Setup (Supabase / Neon PostgreSQL)
1. Create a PostgreSQL database instance on [Supabase](https://supabase.com) or [Neon](https://neon.tech).
2. Copy the connection string into `DATABASE_URL`.
3. The FastAPI app automatically runs non-destructive schema migrations on startup.

### 2. File Storage Setup (Supabase Storage / AWS S3)
1. Create an S3 bucket or Supabase Storage bucket named `documents`.
2. Set `STORAGE_TYPE=s3` or `STORAGE_TYPE=supabase` along with access keys in environment variables.

### 3. FastAPI Backend Deployment (Render / Railway)
1. Link your GitHub repository to [Render](https://render.com) or [Railway](https://railway.app).
2. Choose **Docker** environment.
3. Configure environment variables (`GROQ_API_KEY`, `PINECONE_API_KEY`, `DATABASE_URL`, `STORAGE_TYPE`, etc.).
4. Deploy service. Note down your backend URL (e.g. `https://eda-backend.onrender.com`).

### 4. Next.js Frontend Deployment (Vercel)
1. Import `frontend/` directory into [Vercel](https://vercel.com).
2. Set Environment Variable:
   ```env
   NEXT_PUBLIC_API_URL=https://eda-backend.onrender.com
   ```
3. Deploy frontend.

---

## 6. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health check and operational status |
| `POST` | `/api/documents/upload` | Upload document file or ZIP archive (Rate: 10/min) |
| `GET` | `/api/documents` | List all registered documents |
| `GET` | `/api/documents/{id}/status` | Poll document ingestion stage status |
| `GET` | `/api/documents/{id}/markdown` | Retrieve raw normalized Markdown representation |
| `DELETE` | `/api/documents/{id}` | Delete document, stored files, DB records, and Pinecone namespace |
| `POST` | `/api/chat/stream` | Stream Q&A answer via Server-Sent Events (SSE) (Rate: 20/min) |
| `GET` | `/api/chat/{id}/history` | Retrieve recent chat history session |

---

## 7. Troubleshooting & Verification

* **Tesseract OCR Error**: Ensure Tesseract binary is installed locally (`apt-get install tesseract-ocr` or Windows installer) if analyzing image files (`.png`, `.jpg`).
* **Pinecone Index Mismatch**: The backend automatically auto-detects vector dimension mismatches and re-initializes the index if needed.
* **Rate Limits**: Rate limits are set to 10 uploads/min and 20 query streams/min. Customize limits in `backend/app/routes/upload.py` and `backend/app/routes/chat.py`.
