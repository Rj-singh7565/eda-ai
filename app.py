"""
Root Application Wrapper — Delegates to backend/app/main.py for full backward compatibility with uvicorn app:app and pytest.
"""

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
