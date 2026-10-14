"""
Unified Development Runner for AI-Based EDA Assistant.
Starts:
  1. FastAPI Backend on http://localhost:8000 (app.py)
  2. Next.js Frontend on http://localhost:3000 (frontend/dev-server.js)
Handles graceful shutdown of both servers on CTRL+C or process termination.
"""
import os
import sys
import subprocess
import threading
import time
import signal

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def stream_output(process, prefix):
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"{prefix} {line.rstrip()}", flush=True)
    except Exception:
        pass

def main():
    print("=" * 60)
    print("  Starting AI-Based EDA Assistant (Backend + Frontend)")
    print("=" * 60)

    # 1. Start Backend
    print("[RUNNER] Launching FastAPI Backend on http://localhost:8000...")
    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"
    backend_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=backend_env,
        bufsize=1
    )

    # 2. Start Frontend
    print("[RUNNER] Launching Next.js Frontend on http://localhost:3000...")
    frontend_env = os.environ.copy()
    frontend_env["PORT"] = "3000"
    frontend_proc = subprocess.Popen(
        ["node", "dev-server.js"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=frontend_env,
        bufsize=1
    )

    t_backend = threading.Thread(target=stream_output, args=(backend_proc, "[BACKEND]"), daemon=True)
    t_frontend = threading.Thread(target=stream_output, args=(frontend_proc, "[FRONTEND]"), daemon=True)
    t_backend.start()
    t_frontend.start()

    print("\n[RUNNER] Services initializing:")
    print("  Backend API:   http://localhost:8000 (API Docs at http://localhost:8000/docs)")
    print("  Web Frontend:  http://localhost:3000")
    print("  Press CTRL+C to stop both services.\n", flush=True)

    def shutdown(sig=None, frame=None):
        print("\n[RUNNER] Shutting down services...", flush=True)
        try:
            backend_proc.terminate()
        except Exception:
            pass
        try:
            frontend_proc.terminate()
        except Exception:
            pass
        time.sleep(1)
        try:
            backend_proc.kill()
        except Exception:
            pass
        try:
            frontend_proc.kill()
        except Exception:
            pass
        print("[RUNNER] All services stopped.", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            b_code = backend_proc.poll()
            f_code = frontend_proc.poll()
            if b_code is not None:
                print(f"[RUNNER] Backend exited with code {b_code}", flush=True)
                shutdown()
            if f_code is not None:
                print(f"[RUNNER] Frontend exited with code {f_code}", flush=True)
                shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()
