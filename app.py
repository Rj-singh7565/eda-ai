"""
Root Application Wrapper — Delegates to backend/app/main.py for full backward compatibility with uvicorn app:app and pytest.
"""

import os
import sys

# Ensure local venv packages are accessible if started with global Python
_venv_site = os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
