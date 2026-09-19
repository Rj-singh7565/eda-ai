"""
FastAPI Backend Main Application.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.app import config
from backend.app.routes import health, upload, documents, chat
from backend.app.services import embeddings, retrieval


def _background_warmup():
    try:
        embeddings.warmup_embeddings()
        retrieval.get_pinecone_index()
        print("[STARTUP] Engine pre-warming complete. Vector retrieval ready.")
    except Exception as e:
        print(f"[STARTUP WARN] Startup pre-warm note: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm embedding model and vector store handles in background task for instant server startup."""
    port = int(os.getenv("PORT", 8000))
    print(f"[STARTUP] FastAPI backend ready on port {port}")
    asyncio.create_task(asyncio.to_thread(_background_warmup))
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI-Based EDA Assistant",
    description="Enterprise Document Intelligence RAG Engine with Page/Slide/Row Citations",
    version="2.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration — Production-ready with Vercel & localhost support
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if config.FRONTEND_URL:
    clean_frontend = config.FRONTEND_URL.strip().rstrip("/")
    if clean_frontend and clean_frontend not in allowed_origins:
        allowed_origins.append(clean_frontend)

if config.CORS_ORIGINS:
    for origin in config.CORS_ORIGINS.split(","):
        clean_o = origin.strip().rstrip("/")
        if clean_o and clean_o not in allowed_origins:
            allowed_origins.append(clean_o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
async def home(request: Request):
    """Root access handler — Redirects to deployed frontend if configured, else returns service info."""
    if config.FRONTEND_URL:
        return RedirectResponse(url=config.FRONTEND_URL)
    return {
        "service": "AI-Based EDA Assistant API",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
