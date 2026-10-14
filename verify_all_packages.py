import sys
import importlib

packages_to_check = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "python-dotenv": "dotenv",
    "pypdf": "pypdf",
    "pdfplumber": "pdfplumber",
    "python-docx": "docx",
    "python-pptx": "pptx",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "pytesseract": "pytesseract",
    "Pillow": "PIL",
    "pinecone": "pinecone",
    "sentence-transformers": "sentence_transformers",
    "groq": "groq",
    "jinja2": "jinja2",
    "python-multipart": "multipart",
    "tenacity": "tenacity",
    "slowapi": "slowapi",
    "psycopg2-binary": "psycopg2",
    "boto3": "boto3",
    "pytest": "pytest",
    "httpx": "httpx",
    "duckdb": "duckdb",
    "redis": "redis",
    "orjson": "orjson"
}

missing = []
installed = []

for pkg_name, module_name in packages_to_check.items():
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", "installed")
        installed.append(f"  [OK] {pkg_name} ({module_name}) -> v{ver}")
    except ImportError as e:
        missing.append((pkg_name, str(e)))

print("=" * 60)
print(f"REQUIREMENTS CHECK: {len(installed)} / {len(packages_to_check)} Installed")
print("=" * 60)
for item in installed:
    print(item)

if missing:
    print("\nMISSING PACKAGES:")
    for pkg, err in missing:
        print(f"  [MISSING] {pkg}: {err}")
else:
    print("\nALL PYTHON REQUIREMENTS ARE FULLY INSTALLED AND WORKING!")
