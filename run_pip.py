"""
Helper script to install and verify all Python requirements from requirements.txt.
"""
import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    print("=" * 60)
    print(" [PIP] Installing & Verifying Requirements from requirements.txt")
    print("=" * 60)

    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_file):
        print(f"Error: Could not find requirements file at {req_file}")
        sys.exit(1)

    cmd = [sys.executable, "-m", "pip", "install", "-r", req_file, "--user"]
    print(f"Running: {' '.join(cmd)}\n")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

    for line in iter(process.stdout.readline, ''):
        if line:
            print(line.rstrip())

    process.wait()
    print("\n" + "=" * 60)
    if process.returncode == 0:
        print(" [SUCCESS] All requirements are satisfied and ready!")
    else:
        print(f" [WARNING] Finished with exit code {process.returncode}")
    print("=" * 60)

if __name__ == "__main__":
    main()
