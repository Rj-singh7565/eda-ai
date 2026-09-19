"""
Root Application Wrapper — Delegates to backend/app/main.py for full backward compatibility with uvicorn app:app and pytest.
"""

import os
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
