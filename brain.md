# 🧠 EDA Assistant — Master Project Brain (`brain.md`)

> **Single Source of Truth for the entire EDA Assistant (Enterprise Document Analysis & Intelligence) codebase.**  
> **Instructions for AI & Developers**: Whenever building features, fixing bugs, or refactoring, **read this file first**. It contains an exhaustive reference of all files, services, components, data flows, APIs, and conventions in this repository.

---

## 📑 Table of Contents
1. [Project Overview & Core Mission](#1-project-overview--core-mission)
2. [Master File & Directory Tree](#2-master-file--directory-tree)
3. [Exhaustive File-by-File Catalog](#3-exhaustive-file-by-file-catalog)
4. [System Architecture & End-to-End Data Flows](#4-system-architecture--end-to-end-data-flows)
5. [Backend Deep-Dive (`backend/app/`)](#5-backend-deep-dive-backendapp)
6. [Frontend Deep-Dive (`frontend/`)](#6-frontend-deep-dive-frontend)
7. [Database Schema & Data Persistence](#7-database-schema--data-persistence)
8. [Configuration & Environment Variables](#8-configuration--environment-variables)
9. [Development, Execution & Testing](#9-development-execution--testing)
10. [AI Guidelines & Golden Rules](#10-ai-guidelines--golden-rules)

---

## 1. Project Overview & Core Mission

**EDA Assistant** (Enterprise Document Analysis Assistant) is a high-performance, citation-accurate Retrieval-Augmented Generation (RAG) platform. It allows users to upload single documents or bulk ZIP archives of heterogeneous file formats, processes them into unified semantic Markdown with coordinate markers (Page, Slide, Row, Paragraph), indexes them in a vector database, and enables real-time conversational Q&A with verifiable, deep-linked citations and side-by-side source reading.

### Key Capabilities:
- **Multi-Format Extraction**: Supports `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, and `.zip` archives.
- **Magic-Byte Detection**: Identifies file types using binary header signatures rather than trusting spoofable file extensions.
- **Unified Markdown Normalization**: Transforms heterogeneous document structures into a normalized Markdown representation with embedded coordinate comments (`<!-- coordinate: page=1 -->`, etc.).
- **Sub-Document Coordinate Grounding**: Pinpoints citations to exact pages, slide numbers, or table row indices.
- **Local Dense Embeddings**: Generates 384-dimensional vector embeddings locally using `BAAI/bge-small-en-v1.5` without external API dependency or latency.
- **Namespace-Isolated Vector Search**: Queries vector records in Pinecone using dedicated `doc_id` namespaces for instant filtering and safe multi-tenancy.
- **Fast SSE Q&A Streaming**: Streams LLM answers token-by-token via Server-Sent Events (SSE) powered by Groq (`openai/gpt-oss-120b` or Gemini).
- **Multi-Turn Document Memory**: Retains the last 4 Q&A turns per document session for coherent contextual dialogue.
- **Next.js 14 Premium UI**: Dark/light themed workspace with 340px document sidebar, side-by-side chat & source reader, drag-and-drop upload zone, interactive citation chips, and slide-out evidence drawer.

---

## 2. Master File & Directory Tree

```
edaa/
├── .env                              # Active environment variables (API keys, DB URLs)
├── .env.example                      # Template for required environment variables
├── .gitignore                        # Git exclusion rules
├── AGENTS.md                         # Project rules, design system guidelines, and constraints
├── app.py                            # Backward-compatible entry wrapper -> backend/app/main.py
├── config.py                         # Backward-compatible config wrapper -> backend/app/config.py
├── database.py                       # Backward-compatible database wrapper -> backend/app/database/database.py
├── ingestion.py                      # Backward-compatible ingestion wrapper -> backend/app/services/ingestion.py
├── rag.py                            # Backward-compatible RAG wrapper -> backend/app/services/retrieval.py
├── retrieval.py                      # Backward-compatible retrieval wrapper -> backend/app/services/retrieval.py
├── eda_assistant.db                  # Local SQLite database (documents & chat history)
├── Dockerfile                        # Multi-stage production container configuration
├── docker-compose.yml                # Docker Compose orchestration
├── package.json                      # Monorepo root scripts (concurrently dev, build, start)
├── package-lock.json                 # Root npm lockfile
├── requirements.txt                  # Python dependencies
├── vercel.json                       # Vercel deployment configuration
├── EDA_Assistant_UI_PDA.md           # UI/UX Product Design Architecture specification
├── PDA.md                            # Product Design Architecture specification
├── PROJECT_OVERVIEW.txt              # High-level architecture and component inventory
├── README.md                         # User guide, architecture overview, and setup manual
├── brain.md                          # 🧠 Master System Brain & Single Source of Truth (THIS FILE)
│
├── backend/                          # FastAPI Backend Root
│   └── app/
│       ├── __init__.py
│       ├── main.py                   # FastAPI app definition, CORS, lifespan warmup, routes mounting
│       ├── config.py                 # Configuration, path constants, model hyperparameters, env validation
│       │
│       ├── database/                 # Database Persistence Layer
│       │   ├── __init__.py
│       │   ├── database.py           # Dual SQLite/PostgreSQL CRUD engine & connection pooling
│       │   └── models.py             # DocumentModel & chat history data structures
│       │
│       ├── routes/                   # FastAPI API Endpoints
│       │   ├── __init__.py
│       │   ├── health.py             # Health check & system diagnostic endpoint (/health)
│       │   ├── upload.py             # File upload, ZIP unpacker, magic byte validation (/upload, /api/documents/upload)
│       │   ├── documents.py          # Document lifecycle: status, list, markdown retrieval, delete (/documents)
│       │   └── chat.py               # SSE streaming Q&A and chat session history (/ask/stream, /documents/{id}/history)
│       │
│       ├── schemas/                  # Pydantic Request/Response Models
│       │   ├── __init__.py
│       │   ├── chat.py               # QuestionStreamRequest schema
│       │   └── document.py           # DocumentResponse, DocumentStatusResponse schemas
│       │
│       └── services/                 # Core Business Logic & Pipelines
│           ├── __init__.py
│           ├── dataset_engine.py     # Deterministic DataFrame operations (Filter, Aggregations, GroupBy), 100% column preservation & schema inspector
│           ├── query_router.py       # Query intent classifier and schema-aware operation planner (Structured vs Document RAG)
│           ├── ingestion.py          # Document ingestion pipeline orchestrator & format detector
│           ├── extraction.py         # Multi-format parsers (PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, Image OCR)
│           ├── normalization.py      # Unified Markdown conversion with coordinate marker injection
│           ├── chunking.py           # Semantic coordinate-aware text chunking with overlap
│           ├── embeddings.py         # Local HuggingFace sentence transformer (BAAI/bge-small-en-v1.5)
│           ├── retrieval.py          # Adaptive Multi-Tier Search (Vector -> Lexical Markdown -> Structured Dataset fallback)
│           ├── llm.py                # LLM client & SSE streamer integrating Query Router, DataFrame Engine & AI insights
│           └── storage.py            # Storage driver abstraction (Local, S3, Supabase)
│
├── frontend/                         # Next.js 14 TypeScript Frontend
│   ├── package.json                  # Next.js, React 18, Lucide React dependencies
│   ├── package-lock.json             # Frontend npm lockfile
│   ├── tsconfig.json                 # TypeScript compiler configuration
│   ├── vercel.json                   # Frontend-specific Vercel configuration
│   │
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout with Inter font and HTML metadata
│   │   ├── globals.css               # Vanilla CSS design system (tokens, animations, dark/light theme)
│   │   └── page.tsx                  # Master Dashboard state machine & layout coordinator
│   │
│   ├── components/                   # React UI Components
│   │   ├── NavSidebar.tsx            # Left navigation rail (compact icon-only 64px rail on Analysis page; standard 260px sidebar on other tabs)
│   │   ├── GlobalHeader.tsx          # Compact header on Analysis (title, dataset switcher, Engine Ready badge, icon actions, RS avatar); standard header on other tabs
│   │   ├── analysis/                 # Pixel-Perfect Analysis Workspace Components
│   │   │   ├── AnalysisWorkspace.tsx # Full viewport analysis workspace with centered empty state (5 suggestion chips in 2 rows) & turn cards feed
│   │   │   ├── AnalysisTurnCard.tsx  # Turn Card with Table, Chart, SQL view toggles, Latency badge & Insight callouts
│   │   │   └── CommandBar.tsx        # Clean fixed bottom input bar with left Sparkles icon, placeholder, paperclip attachment & Run Query button
│   │   ├── dashboard/                # Dashboard Modular Views
│   │   │   ├── OverviewDashboard.tsx # Master Overview with KPI cards, Recent Datasets, Activity Feed, Health Summary, Quick Start, Dropzone
│   │   │   ├── DatasetsView.tsx      # Comprehensive dataset library management table
│   │   │   ├── HistoryView.tsx       # Conversation analysis history archive
│   │   │   ├── StorageView.tsx       # Local disk and vector DB storage allocation view
│   │   │   └── SettingsView.tsx      # System hyperparameters and configuration inspector
│   │   ├── ChatWindow.tsx            # Chat messages viewport, auto-scroll container, empty state
│   │   ├── ChatMessage.tsx           # User/Assistant chat bubble renderer with markdown & citation chips
│   │   ├── ChatInput.tsx             # Floating prompt input box, quick suggestions, auto-resizing
│   │   ├── CitationsPanel.tsx        # Slide-out citation drawer with detailed evidence excerpts
│   │   ├── CitationCard.tsx          # Grounded coordinate citation card with similarity metrics
│   │   ├── SourceViewer.tsx          # Markdown workspace reader with coordinate markers & citation highlight
│   │   ├── DocumentViewer.tsx        # Fullscreen Markdown preview modal dialog
│   │   └── ProcessingStatus.tsx      # Real-time ingestion progress stepper
│   │
│   └── lib/                          # Frontend Utilities & API Client
│       ├── api.ts                    # HTTP / SSE client communicating with FastAPI backend (/api/stats, /api/documents, etc.)
│       └── types.ts                  # TypeScript interfaces (DashboardStats, Document, ChatMessage, Citation, etc.)
│
├── static/                           # Legacy Vanilla JS/CSS assets (monolith fallback)
│   ├── script.js                     # Legacy frontend client logic
│   └── style.css                     # Legacy stylesheet
│
├── templates/                        # Legacy HTML templates
│   └── index.html                    # Legacy single-page HTML interface
│
├── tests/                            # Automated Pytest Suite
│   ├── test_pipeline.py              # End-to-end ingestion and RAG streaming tests
│   ├── test_multi_format.py          # Multi-format parser tests (PDF, DOCX, PPTX, XLSX, CSV, Images, ZIP)
│   └── test_normalization.py         # Markdown normalization and coordinate preservation tests
│
├── uploads/                          # Local file storage for uploaded raw documents
└── processed/                        # Local file storage for generated normalized Markdown files
```

---

## 3. Exhaustive File-by-File Catalog

### 3.1 Root Files

| File Path | Purpose | Key Exports / Responsibilities |
|---|---|---|
| `package.json` | Project root task runner. | Runs `concurrently` to launch backend (`python app.py`) on port 8000 and frontend (`next dev`) on port 3000 simultaneously via `npm run dev`. |
| `requirements.txt` | Python dependencies. | Contains all backend packages: `fastapi`, `uvicorn`, `sentence-transformers`, `torch`, `pinecone-client`, `groq`, `pydantic`, `slowapi`, `psycopg2-binary`, `PyPDF2`, `python-docx`, `python-pptx`, `openpyxl`, `pandas`, `pytest`, `httpx`, `google-generativeai`, `pillow`, `boto3`, `supabase`. |
| `app.py` | Root application entry point. | Re-exports `app` from `backend.app.main` and runs Uvicorn on `0.0.0.0:8000` with hot-reloading when executed directly. |
| `config.py` | Legacy config shim. | Re-exports all variables from `backend.app.config` for backward compatibility. |
| `database.py` | Legacy database shim. | Re-exports functions from `backend.app.database.database` for backward compatibility. |
| `ingestion.py` | Legacy ingestion shim. | Re-exports functions from `backend.app.services.ingestion` for backward compatibility. |
| `rag.py` / `retrieval.py` | Legacy retrieval shims. | Re-export functions from `backend.app.services.retrieval` for backward compatibility. |
| `AGENTS.md` | AI Agent & Developer Rules. | Defines strict project guidelines: preserve 340px split pane layout, dark/light themes, Inter font, `#6366f1` accent, vanilla CSS only (no Tailwind), and chat bubble styles. |
| `eda_assistant.db` | Local SQLite database. | Persistent storage for document records and chat turns when PostgreSQL is not configured. |
| `Dockerfile` | Containerization. | Multi-stage production container setup for containerized deployment. |
| `docker-compose.yml` | Multi-container setup. | Orchestrates backend, database, and local dependencies. |
| `vercel.json` | Deployment settings. | Configuration for cloud hosting on Vercel. |
| `EDA_Assistant_UI_PDA.md` | UI Architecture Document. | In-depth design spec for all UI components, interactions, state transitions, and responsive layout. |
| `PDA.md` | Product Architecture Spec. | Architectural specification of the entire RAG pipeline, coordinates, and schemas. |
| `PROJECT_OVERVIEW.txt` | Overview inventory. | High-level summary of the codebase components. |
| `README.md` | Documentation. | User guide, feature highlights, installation steps, and API endpoint references. |

---

### 3.2 Backend Implementation (`backend/app/`)

#### 📁 `backend/app/`
- **`main.py`**:
  - Initializes FastAPI application instance with custom title, version, and lifespan.
  - Implements `lifespan` context manager that triggers `_background_warmup()` to pre-load the BGE embedding model into memory and warm up Pinecone connection asynchronously.
  - Configures SlowAPI rate limiting (`Limiter(key_func=get_remote_address)`) and exception handlers.
  - Sets up CORS middleware allowing cross-origin requests from the Next.js frontend.
  - Mounts routes: `health.router`, `upload.router`, `documents.router`, `chat.router`.
  - Root route `GET /` redirects to frontend on `http://localhost:3000`.

- **`config.py`**:
  - Loads `.env` file via `dotenv.load_dotenv()`.
  - Defines and validates required API keys: `GROQ_API_KEY`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`.
  - Sets up Database & Storage configs: `DATABASE_URL`, `STORAGE_TYPE` (`local`, `s3`, `supabase`), S3 credentials, Supabase credentials.
  - Model configurations: `EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"`, `EMBEDDING_DIMENSION = 384`, `LLM_MODEL = "openai/gpt-oss-120b"`.
  - RAG Hyperparameters: `CHUNK_SIZE = 600`, `CHUNK_OVERLAP = 100`, `TOP_K = 5`, `SIMILARITY_THRESHOLD = 0.35`, `MEMORY_TURNS = 4`.
  - File constraints: `MAX_FILE_SIZE_MB = 25`, `MAX_ZIP_FILES = 15`.
  - Supported extensions: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.zip`.
  - Directory path constants: `BASE_DIR`, `UPLOAD_DIR`, `PROCESSED_DIR`, `DB_PATH`.

#### 📁 `backend/app/database/`
- **`database.py`**:
  - Dual-engine database abstraction supporting both PostgreSQL (via `psycopg2`) and SQLite (via standard `sqlite3`).
  - Auto-initializes schema on startup via `init_db()` creating `documents` and `chat_history` tables (with `ON DELETE CASCADE`).
  - Functions:
    - `get_db_connection()`: Connects to PostgreSQL if `DATABASE_URL` starts with `postgres`, otherwise opens `eda_assistant.db`.
    - `create_document(doc_id, filename, file_size, file_type)`: Inserts new document record with status `processing`.
    - `update_document_status(doc_id, status, page_count, chunk_count, error_message, markdown_path)`: Updates progress state.
    - `get_document(doc_id)`: Fetches document dictionary by ID.
    - `list_documents()`: Returns all documents ordered by `created_at DESC`.
    - `delete_document(doc_id)`: Deletes document and cascading chat history.
    - `add_chat_turn(doc_id, question, answer)`: Inserts a Q&A exchange into `chat_history`.
    - `get_recent_chat_history(doc_id, limit)`: Fetches the last `N` Q&A pairs for conversation memory.
- **`models.py`**:
  - `DocumentModel`: Data model class representing a document with attributes (`doc_id`, `filename`, `file_size`, `file_type`, `page_count`, `chunk_count`, `status`, `error_message`, `markdown_path`, `created_at`) and `to_dict()` converter.

#### 📁 `backend/app/routes/`
- **`health.py`**:
  - `GET /health` and `GET /api/health`: Returns JSON health status (`status: "healthy"`, database type, Pinecone index availability, server timestamp).
- **`upload.py`**:
  - `POST /upload` and `POST /api/documents/upload`: Handles file uploads (multipart form data).
  - Validates file size (max 25MB).
  - Inspects file headers via `ingestion.detect_file_type` (magic bytes).
  - **ZIP Archive Unpacker**: Iterates zip entries, skips OS junk (`__MACOSX`, `.DS_Store`, hidden files), deduplicates paths, enforces 15-file limit, generates individual `doc_id`s, saves extracted files, and queues background ingestion for each file.
  - **Single File Handler**: Creates document record in DB, saves raw file, dispatches `background_tasks.add_task(ingestion.process_document_pipeline, doc_id, file_path, detected_type)`.
  - Returns `200 OK` or `207 Multi-Status` with created document metadata.
- **`documents.py`**:
  - `GET /documents` & `GET /api/documents`: Lists all registered documents.
  - `GET /documents/{doc_id}` & `GET /api/documents/{doc_id}/status`: Polling endpoint returning document ingestion status.
  - `GET /documents/{doc_id}/markdown`: Reads and streams the raw normalized Markdown representation of the document.
  - `DELETE /documents/{doc_id}`: Synchronously deletes DB record; offloads disk/cloud file cleanup and Pinecone vector namespace purge to background tasks.
- **`chat.py`**:
  - `POST /ask/stream` & `POST /api/chat/stream`: Accepts `{doc_id, question}`, verifies document status is `ready`, and returns a `StreamingResponse(llm.generate_answer_stream(doc_id, question), media_type="text/event-stream")`.
  - `GET /documents/{doc_id}/history` & `GET /api/chat/{doc_id}/history`: Returns historical Q&A turns for the active document.

#### 📁 `backend/app/schemas/`
- **`chat.py`**: `QuestionStreamRequest` Pydantic model (`doc_id: str`, `question: str`).
- **`document.py`**: `DocumentResponse`, `DocumentStatusResponse` Pydantic models.

#### 📁 `backend/app/services/`
- **`ingestion.py`**:
  - `detect_file_type(file_path)`: Uses magic byte signature inspection (e.g. `%PDF-` for PDF, `PK\x03\x04` with zip inspection for DOCX/PPTX/XLSX, `\x89PNG` for images) with extension fallbacks.
  - `process_document_pipeline(doc_id, file_path, file_type)`: Master pipeline orchestrator. Executes 5 sequential stages:
    1. **Parsing**: Calls `extraction.extract_content(file_path, file_type)`.
    2. **Normalization**: Calls `normalization.to_unified_markdown(raw_content, file_type)` and saves `.md` to storage.
    3. **Chunking**: Calls `chunking.chunk_unified_markdown(markdown_content)`.
    4. **Embedding**: Computes dense vectors via `embeddings.generate_embeddings([c['text'] for c in chunks])`.
    5. **Indexing**: Upserts vector records into Pinecone under `namespace=doc_id` with metadata (`doc_id`, `coordinate_id`, `coordinate_type`, `coordinate_value`, `text_preview`).
    - Updates DB status at each step; catches exceptions and sets status `error` with descriptive message.
- **`extraction.py`**:
  - Multi-format text, table, and coordinate extractor with **Intelligent EDA Profiling for Large Datasets (100,000+ rows)**:
    - **Structured Datasets (CSV / Excel)**:
      - For small tables ($\le 100$ rows): extracts direct Markdown table batches.
      - For large tables ($> 100$ to $100,000+$ rows): executes streaming/chunked ingestion generating 5 high-value semantic EDA sections (**Overview & Schema**, **Descriptive Statistics**, **Categorical Distributions**, **Feature Correlations & Insights**, and **Representative Stratified Samples**), preventing memory blowups and eliminating vector database saturation.
    - **PDF**: Uses PyPDF / pdfplumber to extract text per page and extract structured tables.
    - **DOCX**: Uses `python-docx` to extract paragraphs, heading levels, and table cells.
    - **PPTX**: Uses `python-pptx` to iterate slides, extracting title, body text shapes, and table contents per slide.
    - **Plaintext / Markdown**: Decodes UTF-8 text with paragraph boundaries.
    - **Images**: OCR using Tesseract / Gemini Vision.
- **`normalization.py`**:
  - Converts heterogeneous extracted raw data into standardized **Unified Markdown** with YAML frontmatter.
  - Injects semantic coordinate headers (`## Section`, `## Sheet`, `## Page`) and deduplicates table markdown strings.
- **`chunking.py`**:
  - `chunk_markdown(markdown_text, doc_id, chunk_size, chunk_overlap)`:
  - Splits document into semantic sentence-aware chunks while maintaining table integrity and section coordinate labels.
  - Features duplicate chunk suppression and minimum character thresholds ($\ge 30$ chars) to prevent micro-fragmentation.
- **`embeddings.py`**:
  - Hardware-adaptive `SentenceTransformer("BAAI/bge-small-en-v1.5")` embedding manager.
  - **Hardware Acceleration**: Automatically selects CUDA GPU, Apple MPS, or multi-threaded CPU for matrix computations.
  - **SHA-256 Deduplication & Memory Cache**: Computes SHA-256 hashes of chunk texts, caching up to 10,000 dense vectors to eliminate redundant neural model inference.
  - `generate_embeddings(texts, batch_size)`: Batches unique unseen texts (128-256 batch size) and re-maps existing cached vectors.
- **`retrieval.py`**:
  - Manages Pinecone vector database connection and serverless index creation.
  - `get_pinecone_index()`: Returns Pinecone Index instance.
  - `retrieve_relevant_chunks(doc_id, query, top_k=5, similarity_threshold=0.35)`:
    - Encodes query via `embeddings.generate_query_embedding(query)`.
    - Queries Pinecone within `namespace=doc_id`.
    - Filters results below `similarity_threshold`.
    - Returns retrieved text chunks with similarity scores and coordinate metadata.
- **`llm.py`**:
  - Manages LLM interaction via Groq (`openai/gpt-oss-120b` or Gemini).
  - `generate_answer_stream(doc_id, question)`:
    - Retrieves top matching chunks via `retrieval.retrieve_relevant_chunks()`.
    - Retrieves recent conversation memory via `database.get_recent_chat_history()`.
    - Builds a prompt with strict system instructions:
      - Answer based strictly on the provided context.
      - If unknown, state clearly that the document does not contain the answer.
      - Ground every claim with a citation token: `[[citation: coordinate_id | quote / summary]]`.
    - Sends payload to Groq streaming API.
    - Streams tokens to the client using SSE format: `data: {"token": "..."}\n\n`.
    - Yields a final `data: {"event": "done", "citations": [...]}\n\n` event.
    - Persists the complete question and answer turn in `chat_history`.
- **`storage.py`**:
  - Storage abstraction implementing `LocalStorage`, `S3Storage`, and `SupabaseStorage`.
  - Provides unified methods: `save_raw_file()`, `save_processed_markdown()`, `read_processed_markdown()`, `delete_document_files()`.

---

### 3.3 Frontend Implementation (`frontend/`)

#### 📁 `frontend/app/`
- **`layout.tsx`**: Root layout component configuring Inter font, page title, favicon, and viewport metadata.
- **`globals.css`**: Complete vanilla CSS design system containing:
  - CSS Custom Properties for Dark/Light theme switching (`--bg-app`, `--bg-sidebar`, `--bg-card`, `--accent-primary: #6366f1`, `--text-primary`, `--border-color`, etc.).
  - Layout Grid: Split-pane layout with 340px document sidebar and fluid main workspace.
  - Micro-animations, button hover states, glassmorphic overlays, custom scrollbars.
  - Chat bubble styles: Blue right-aligned user bubbles, bordered assistant bubbles, interactive citation chips.
  - Citation drawer slide-in transitions and Markdown viewer formatting.
- **`page.tsx`**:
  - Master Dashboard state container:
    - Documents list (`documents`), active document (`activeDocId`, `activeDoc`).
    - Chat messages state (`messages`), input text, streaming state.
    - Active workspace view tab: `'chat'` vs `'source'`.
    - Citation drawer open/close state (`isCitationsDrawerOpen`) and active citations (`activeCitations`).
    - Raw Markdown content for active document (`markdownContent`).
    - Polling loop for active documents in `processing`, `parsing`, `normalizing`, `chunking`, `embedding`, `indexing` states.
    - SSE stream reader consuming `/ask/stream` responses token by token.

#### 📁 `frontend/components/`
- **`NavSidebar.tsx`**: Narrow leftmost icon rail (Documents icon, Analytics icon, Settings icon, and Dark/Light Theme toggle).
- **`DocumentSidebar.tsx`**: Left sidebar (340px width).
  - Search input filtering documents by name in real time.
  - List of all uploaded documents with file type icons, status badges, page/chunk counts, and relative timestamps.
  - Context action buttons per document: Open Source View, Delete document.
  - Embedded `UploadZone` trigger at the bottom.
- **`UploadZone.tsx`**: Drag-and-drop file upload target supporting multi-format files and `.zip` archives with upload progress feedback.
- **`DocumentHeader.tsx`**: Top header bar of the active document workspace displaying file name, file size, status badge, page/chunk counters, and tab toggles (Chat vs Source Workspace).
- **`ChatWindow.tsx`**: Chat container rendering the message thread with automatic bottom scrolling, empty welcome state with prompt suggestions, and typing indicator.
- **`ChatMessage.tsx`**:
  - Renders individual user and assistant message bubbles.
  - Parses and renders Markdown text, code blocks with copy buttons, and interactive citation chips `[Page 2]`, `[Slide 5]`, `[Row 12]`.
  - Clicking a citation chip highlights the citation in the side drawer or switches to the Source Viewer.
- **`ChatInput.tsx`**:
  - Floating bottom input bar with auto-expanding textarea, send button, and keyboard shortcut handler (Enter to send, Shift+Enter for newlines).
  - Displays quick suggestion chips when the conversation is empty.
- **`CitationsPanel.tsx`**:
  - Slide-out side drawer on the right displaying all grounded citations for the latest assistant answer.
  - Shows coordinate badges, similarity match percentages, text excerpts, and a button to view in source document.
- **`CitationCard.tsx`**: Individual citation card component displaying coordinate type/value, match score, and formatted excerpt.
- **`SourceViewer.tsx`**:
  - Rich document reading workspace rendering the full normalized Markdown content.
  - Renders visual coordinate section dividers (`Page 1`, `Slide 2`, etc.).
  - Automatically scrolls to and highlights the target coordinate when a user clicks a citation chip.
- **`DocumentWorkspaceReader.tsx`**: Side-by-side workspace combining chat and source reading views.
- **`DocumentViewer.tsx`**: Modal dialog for quick fullscreen Markdown previewing.
- **`ProcessingStatus.tsx`**: Stepper UI showing live document processing phases (Parsing -> Normalizing -> Chunking -> Embedding -> Indexing -> Ready).
- **`EvidenceRuler.tsx`**: Mini visual coordinate timeline / ruler for quick jumping within large documents.
- **`GlobalHeader.tsx`**: Top application bar with EDA Assistant branding, system health indicator, and document metrics.

#### 📁 `frontend/lib/`
- **`types.ts`**: TypeScript definitions:
  - `Document`: `{ doc_id, filename, file_size, file_type, page_count, chunk_count, status, error_message, markdown_path, created_at }`
  - `ChatMessage`: `{ id, sender: 'user' | 'assistant', text, citations?, timestamp }`
  - `Citation`: `{ coordinate_id, coordinate_type, coordinate_value, excerpt, score }`
  - `DocumentStatus`: Status union type.
- **`api.ts`**: Frontend API client functions:
  - `fetchDocuments()`: `GET /api/documents`
  - `fetchDocumentStatus(docId)`: `GET /api/documents/{docId}/status`
  - `fetchDocumentMarkdown(docId)`: `GET /api/documents/{docId}/markdown`
  - `fetchChatHistory(docId)`: `GET /api/chat/{docId}/history`
  - `uploadDocumentFile(file)`: `POST /api/documents/upload`
  - `deleteDocumentRecord(docId)`: `DELETE /api/documents/{docId}`
  - `streamChatQuestion(docId, question, onToken, onCitation, onDone, onError)`: SSE event stream reader.

---

### 3.4 Automated Test Suite (`tests/`)

- **`test_pipeline.py`**: Tests full end-to-end flow: document creation, status updates, markdown storage, chunking, embedding generation, and chat streaming mock.
- **`test_multi_format.py`**: Tests extraction parsers across PDF, DOCX, PPTX, XLSX, CSV, Plaintext, Images, and ZIP archives.
- **`test_normalization.py`**: Tests markdown normalization and verifies coordinate comment injection (`<!-- coordinate: ... -->`).

---

## 4. System Architecture & End-to-End Data Flows

```mermaid
flowchart TD
    User([User / Browser])
    
    subgraph Frontend ["Frontend (Next.js 14 / TypeScript)"]
        UI_Upload[UploadZone / Drag & Drop]
        UI_Sidebar[DocumentSidebar]
        UI_Chat[ChatWindow & ChatInput]
        UI_Source[SourceViewer & Markdown]
        UI_Citations[CitationsPanel]
    end

    subgraph Backend ["FastAPI Backend (:8000)"]
        Router_Upload["/upload (upload.py)"]
        Router_Docs["/documents (documents.py)"]
        Router_Chat["/ask/stream (chat.py)"]
        
        subgraph Pipeline ["Ingestion Pipeline (ingestion.py)"]
            Detect[Magic Byte Detection]
            Extract[Multi-Format Extractor (extraction.py)]
            Normalize[Unified Markdown Normalizer (normalization.py)]
            Chunk[Semantic Chunker (chunking.py)]
            Embed[Local BGE-Small-v1.5 (embeddings.py)]
        end
        
        subgraph RAG ["RAG Query Engine (llm.py & retrieval.py)"]
            Retriever[Pinecone Vector Search]
            Memory[Recent Chat History]
            GroqLLM[Groq / Gemini LLM Streamer]
        end
    end

    subgraph Storage ["Persistence Layer"]
        DB[(SQLite / PostgreSQL)]
        Disk[("uploads/ & processed/ Files")]
        PineconeDB[("Pinecone Vector DB (namespace=doc_id)")]
    end

    %% Flows
    User --> UI_Upload
    UI_Upload -->|POST multipart| Router_Upload
    Router_Upload -->|Register 'processing'| DB
    Router_Upload -->|Save raw file| Disk
    Router_Upload -->|Dispatch BackgroundTask| Pipeline

    Pipeline --> Detect --> Extract --> Normalize
    Normalize -->|Save .md file| Disk
    Normalize --> Chunk --> Embed
    Embed -->|Upsert Vectors + Coordinates| PineconeDB
    Pipeline -->|Update status 'ready'| DB

    UI_Sidebar -->|Poll status & list| Router_Docs
    Router_Docs --> DB
    UI_Source -->|GET /markdown| Router_Docs
    Router_Docs --> Disk

    UI_Chat -->|POST /ask/stream| Router_Chat
    Router_Chat --> Retriever
    Retriever -->|Dense Vector Query| PineconeDB
    Router_Chat --> Memory --> DB
    Router_Chat --> GroqLLM
    GroqLLM -->|SSE Stream tokens & citations| UI_Chat
    UI_Chat --> UI_Citations
    UI_Citations -->|Jump to coordinate| UI_Source
```

---

## 5. Backend Deep-Dive (`backend/app/`)

### 5.1 Document Ingestion Lifecycle
1. **Upload & Magic Byte Check**: File received in `backend/app/routes/upload.py`. First 2048 bytes inspected via `backend/app/services/ingestion.py:detect_file_type()`. If a `.zip` archive is uploaded, it is automatically unzipped, validated, and decomposed into up to 15 discrete documents.
2. **Database Registration**: Document is inserted into `documents` table with status `processing`.
3. **Async Background Dispatch**: FastAPI `BackgroundTasks` launches `ingestion.process_document_pipeline(doc_id, file_path, detected_type)`.
4. **Extraction**: `extraction.extract_content()` invokes the parser matching `detected_type` (PDF, Word, PowerPoint, Excel, CSV, Plaintext, OCR).
5. **Normalization**: `normalization.to_unified_markdown()` outputs a clean Markdown string with embedded coordinate headers (`<!-- coordinate: page=N -->`).
6. **Storage**: Markdown file written to `processed/{doc_id}.md` via `storage.storage_service`.
7. **Semantic Chunking**: `chunking.chunk_unified_markdown()` creates ~600 character chunks with 100 character overlap, propagating coordinate metadata into each chunk.
8. **Vector Embeddings**: `embeddings.generate_embeddings()` computes 384-dimensional embeddings using `BAAI/bge-small-en-v1.5`.
9. **Pinecone Indexing**: Vectors are upserted into Pinecone with `namespace=doc_id`. Metadata includes `coordinate_id`, `coordinate_type`, `coordinate_value`, and text snippets.
10. **Status Ready**: Database is updated with `status = 'ready'`, `page_count`, and `chunk_count`.

### 5.2 RAG Retrieval & Streaming Q&A
1. **Client Request**: Frontend calls `POST /ask/stream` with `{ doc_id, question }`.
2. **Validation**: Backend checks that document exists and `status == 'ready'`.
3. **Query Embedding & Retrieval**: Query is embedded via BGE-small and queried in Pinecone with `namespace=doc_id`, `top_k=5`, and `similarity_threshold=0.35`.
4. **Memory Injection**: Previous 4 Q&A turns are retrieved from `chat_history` via `database.get_recent_chat_history()`.
5. **Prompt Assembly**: Constructs system instructions strictly binding the model to context and enforcing `[[citation: coordinate_id | quote]]` citations.
6. **SSE Stream Generation**: Groq API streams response chunks formatted as `data: {"token": "..."}\n\n`.
7. **Citation Parsing & Event**: Citations in the response are parsed and emitted in a final `data: {"event": "done", "citations": [...]}\n\n` event.
8. **Persistence**: Complete Q&A pair is saved into `chat_history`.

---

## 6. Frontend Deep-Dive (`frontend/`)

### 6.1 Design System & Guidelines (Per `AGENTS.md`)
- **Layout**: Split-pane layout with 340px left document sidebar and fluid right workspace.
- **Typography**: Inter (`font-family: 'Inter', sans-serif`).
- **Colors**:
  - Primary Accent: Indigo/Violet (`#6366f1` / `hsl(243, 75%, 59%)`).
  - Dark Theme: App Background `#0a0b10`, Sidebar `#10121a`, Card `#161926`, Border `#24293d`.
  - Light Theme: App Background `#f8fafc`, Sidebar `#f1f5f9`, Card `#ffffff`, Border `#e2e8f0`.
- **CSS Architecture**: Vanilla CSS in `globals.css` with CSS variables. **No CSS frameworks (Tailwind, Bootstrap) allowed.**
- **Chat Bubbles**: User bubbles blue `#6366f1` right-aligned; Assistant bubbles bordered neutral card left-aligned with inline interactive citation chips.

### 6.2 Frontend State Flow (`page.tsx`)
```
DashboardPage (page.tsx)
  ├── documents: Document[] (polled automatically while any doc is processing)
  ├── activeDocId: string | null (controls active document across all components)
  ├── messages: ChatMessage[] (active document chat history + live streaming response)
  ├── markdownContent: string (fetched from /documents/{id}/markdown for Source Viewer)
  ├── activeWorkspaceTab: 'chat' | 'source' (toggles chat view vs full markdown reader)
  ├── isCitationsDrawerOpen: boolean (toggles right slide-out citation drawer)
  └── activeCoordinate: string (syncs highlighted section between citation chips & source viewer)
```

---

## 7. Database Schema & Data Persistence

### 7.1 Schema Definition (PostgreSQL & SQLite)

#### Table: `documents`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `doc_id` | VARCHAR(255) / TEXT | PRIMARY KEY | Unique UUID for document |
| `filename` | TEXT | NOT NULL | Original uploaded filename |
| `file_size` | BIGINT / INTEGER | NOT NULL | Size in bytes |
| `file_type` | VARCHAR(50) / TEXT | NOT NULL DEFAULT 'pdf' | Format (`pdf`, `docx`, `pptx`, `excel`, `csv`, `md`, `image`) |
| `page_count` | INT / INTEGER | DEFAULT 0 | Extracted page / slide / sheet count |
| `chunk_count` | INT / INTEGER | DEFAULT 0 | Total indexed chunks |
| `status` | VARCHAR(50) / TEXT | DEFAULT 'processing' | `processing`, `parsing`, `normalizing`, `chunking`, `embedding`, `indexing`, `ready`, `error` |
| `error_message` | TEXT | NULL | Detailed error description if failed |
| `markdown_path` | TEXT | NULL | Path to normalized Markdown artifact |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Upload timestamp |

#### Table: `chat_history`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL / INTEGER | PRIMARY KEY AUTOINCREMENT | Unique turn ID |
| `doc_id` | VARCHAR(255) / TEXT | REFERENCES documents(doc_id) ON DELETE CASCADE | Target document ID |
| `question` | TEXT | NOT NULL | User's prompt |
| `answer` | TEXT | NOT NULL | Assistant's response with citations |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Message timestamp |

---

## 8. Configuration & Environment Variables

| Variable Name | Required | Default Value | Description |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | — | Groq API Key for high-speed LLM inference. |
| `PINECONE_API_KEY` | **Yes** | — | Pinecone API Key for vector search. |
| `PINECONE_INDEX_NAME` | No | `eda-assistant` | Target Pinecone Serverless Index name. |
| `GEMINI_API_KEY` | No | — | Google Gemini API Key (multimodal OCR / LLM fallback). |
| `DATABASE_URL` | No | `sqlite:///eda_assistant.db` | PostgreSQL connection string (`postgresql://user:pass@host:5432/db`). If unset, uses local SQLite. |
| `STORAGE_TYPE` | No | `local` | Storage driver (`local`, `s3`, `supabase`). |
| `LLM_MODEL` | No | `openai/gpt-oss-120b` | Model identifier for Groq LLM inference. |
| `S3_BUCKET` | No | — | AWS S3 / Cloudflare R2 bucket name (when `STORAGE_TYPE=s3`). |
| `AWS_ACCESS_KEY_ID` | No | — | AWS / S3 Access Key. |
| `AWS_SECRET_ACCESS_KEY`| No | — | AWS / S3 Secret Key. |
| `SUPABASE_URL` | No | — | Supabase Project URL (when `STORAGE_TYPE=supabase`). |
| `SUPABASE_KEY` | No | — | Supabase Service / Anon API Key. |

---

## 9. Development, Execution & Testing

### 9.1 Local Development
To run both backend (port 8000) and frontend (port 3000) simultaneously:
```bash
npm run dev
```

To run components individually:
- **Backend**: `python app.py` or `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Frontend**: `npm run dev --prefix frontend` (runs Next.js on `http://localhost:3000`)

### 9.2 Running Automated Tests
```bash
pytest tests/ -v
```

### 9.3 Building for Production
- **Frontend Build**: `npm run build`
- **Frontend Start**: `npm run start`

---

## 10. AI Guidelines & Golden Rules

When modifying or expanding this codebase, strictly observe the following rules:

1. **Do NOT scan the entire codebase**: Read this `brain.md` file first to locate the exact components, routes, and services you need to edit.
2. **Preserve the UI Design Language**:
   - Never introduce Tailwind CSS, Bootstrap, or other CSS frameworks. Use vanilla CSS and CSS variables defined in `frontend/app/globals.css`.
   - Maintain the 340px document sidebar on the left and split-pane workspace.
   - Keep the dark/light theme CSS custom properties (`--bg-app`, `--accent-primary: #6366f1`, etc.).
3. **Respect Coordinate Grounding**:
   - Any new document format parser added to `extraction.py` MUST output coordinate markers compatible with `normalization.py` (`page`, `slide`, `row`, `paragraph`).
   - Any chunking modifications in `chunking.py` MUST preserve coordinate metadata in chunk headers.
4. **Maintain Backward-Compatible Root Wrappers**:
   - Keep `app.py`, `config.py`, `database.py`, `ingestion.py`, `rag.py`, and `retrieval.py` at the root as delegation wrappers to `backend/app/*`.
5. **Always Keep Vectors Namespace-Isolated**:
   - Vector upserts and queries in Pinecone MUST always specify `namespace=doc_id` to maintain document isolation and avoid cross-contamination.
6. **Keep Ingestion Asynchronous**:
   - Heavy parsing, embedding, and indexing work must run in background tasks (`BackgroundTasks` or thread pool) so that HTTP upload requests return immediately with `status: "processing"`.

---
*Last updated: 2026-09-01 | Maintained for EDA Assistant Project*
