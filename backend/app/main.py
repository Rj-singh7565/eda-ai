"""
FastAPI Backend Main Application.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.app.routes import health, upload, documents, chat

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI-Based EDA Assistant",
    description="Enterprise Document Intelligence RAG Engine with Page/Slide/Row Citations",
    version="2.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Templates setup for standalone execution
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir) if os.path.exists(templates_dir) else None

# Include Routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
async def home(request: Request):
    """Serve split-pane workspace HTML UI when accessed directly."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return {"message": "AI EDA Assistant FastAPI Backend operational.", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
