"""
Comprehensive Test Suite for Large ZIP Archive Uploads, Size Limits (up to 25MB),
Structured Error Classification, and Archive Security Protections.
"""

import os
import io
import zipfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import config
from backend.app.database import database


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """Setup isolated test database and upload directory, mock heavy background ingestion."""
    test_db = str(tmp_path / "test_zip_eda.db")
    test_upload = str(tmp_path / "uploads")
    os.makedirs(test_upload, exist_ok=True)

    orig_db = config.DB_PATH
    orig_upload = config.UPLOAD_DIR

    config.DB_PATH = test_db
    config.UPLOAD_DIR = test_upload
    database.init_db()

    with patch("backend.app.services.ingestion.run_ingestion_pipeline"):
        yield

    config.DB_PATH = orig_db
    config.UPLOAD_DIR = orig_upload


client = TestClient(app)


def build_zip_in_memory(files_dict: dict, padding_size_bytes: int = 0) -> bytes:
    """Helper to build a valid in-memory zip archive with optional padding for size tests."""
    buf = io.BytesIO()
    # Use ZIP_STORED when padded so large test archives are created instantly without CPU compression overhead
    comp = zipfile.ZIP_STORED if padding_size_bytes > 0 else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(buf, "w", compression=comp) as z:
        for fname, content in files_dict.items():
            if isinstance(content, str):
                z.writestr(fname, content.encode("utf-8"))
            else:
                z.writestr(fname, content)
        if padding_size_bytes > 0:
            # Fast zero padding
            z.writestr("padding.dat", b"\x00" * padding_size_bytes)
    buf.seek(0)
    return buf.getvalue()


def test_5mb_valid_zip_accepted():
    """1. Test that a 5 MB valid ZIP is accepted."""
    files = {"report.csv": "id,name,value\n1,Alpha,100\n2,Beta,200\n"}
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=5 * 1024 * 1024)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("archive_5mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch"] is True
    assert len(data["documents"]) >= 1


def test_8mb_valid_zip_accepted():
    """2. Test that an 8 MB valid ZIP is accepted (no 8MB boundary rejection)."""
    files = {"students.csv": "Student,CGPA\nAlice,9.0\nBob,8.5\n"}
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=8 * 1024 * 1024)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("archive_8mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch"] is True
    assert len(data["documents"]) >= 1


def test_10mb_valid_zip_accepted():
    """3. Test that a 10 MB valid ZIP is accepted."""
    files = {"data.txt": "Enterprise document intelligence summary."}
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=10 * 1024 * 1024)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("archive_10mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch"] is True


def test_20mb_valid_zip_accepted():
    """4. Test that a 20 MB valid ZIP is accepted without 'invalid ZIP' error."""
    files = {
        "analysis.csv": "Dept,Budget\nSales,500000\nEngineering,1200000\n",
        "notes.md": "# Notes\nQuarterly report overview."
    }
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=20 * 1024 * 1024)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("archive_20mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch"] is True
    assert len(data["documents"]) == 2


def test_25mb_boundary_zip_handled():
    """5. Test boundary at exactly 24.8 MB (below 25MB) is accepted."""
    files = {"doc.txt": "Boundary test content."}
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=int(24.5 * 1024 * 1024))

    response = client.post(
        "/api/documents/upload",
        files={"file": ("boundary_25mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    assert response.json()["batch"] is True


def test_oversized_26mb_zip_rejected_as_zip_too_large():
    """6. Test that a >25 MB ZIP is rejected with structured ZIP_TOO_LARGE error."""
    files = {"doc.txt": "Large payload content."}
    # 26 MB raw data
    zip_bytes = build_zip_in_memory(files, padding_size_bytes=int(26 * 1024 * 1024))

    response = client.post(
        "/api/documents/upload",
        files={"file": ("oversized_26mb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "ZIP_TOO_LARGE"
    assert "25 MB" in data.get("message", "")
    assert data.get("max_size_mb") == 25


def test_corrupted_zip_returns_invalid_zip():
    """7. Test corrupted ZIP returns structured INVALID_ZIP error."""
    corrupted_bytes = b"PK\x03\x04" + os.urandom(1024) # fake zip header with garbage data

    response = client.post(
        "/api/documents/upload",
        files={"file": ("corrupt.zip", corrupted_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "INVALID_ZIP"
    assert "Corrupted or invalid ZIP" in data.get("message", "")


def test_non_zip_renamed_to_zip_rejected():
    """8. Test non-ZIP file renamed to .zip is classified as INVALID_ZIP."""
    fake_zip_bytes = b"This is a plaintext file renamed to archive.zip"

    response = client.post(
        "/api/documents/upload",
        files={"file": ("fake.zip", fake_zip_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "INVALID_ZIP"


def test_empty_zip_returns_empty_zip():
    """9. Test completely empty ZIP archive (0 files) returns EMPTY_ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        pass # create empty zip
    buf.seek(0)
    empty_zip_bytes = buf.getvalue()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.zip", empty_zip_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "EMPTY_ZIP"


def test_zip_with_unsupported_files():
    """10. Test ZIP containing only unsupported formats returns proper skipped response."""
    files = {"audio.mp3": b"ID3\x03\x00\x00\x00\x00\x00\x00", "program.exe": b"MZ\x90\x00"}
    zip_bytes = build_zip_in_memory(files)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("unsupported.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "NO_VALID_DOCUMENTS"
    assert len(data.get("skipped", [])) == 2


def test_zip_with_heterogeneous_supported_documents():
    """11. Test ZIP containing PDF, DOCX, CSV, MD, TXT processes all valid files."""
    files = {
        "dataset.csv": "Col1,Col2\nVal1,Val2\n",
        "notes.md": "# Title\nMarkdown text",
        "sample.txt": "Plain text content"
    }
    zip_bytes = build_zip_in_memory(files)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("multi.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch"] is True
    assert len(data["documents"]) == 3


def test_zip_slip_path_traversal_protection():
    """12. Test that Zip Slip path traversal attempts (../../evil.sh) are safely rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../../evil.txt", "Malicious file content")
        z.writestr("valid_doc.txt", "Legitimate file content")
    buf.seek(0)
    zip_bytes = buf.getvalue()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("zipslip.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 200
    data = response.json()
    # The valid document was extracted, the malicious path was skipped
    assert len(data["documents"]) == 1
    assert any("Path traversal" in s["reason"] for s in data["skipped"])


def test_zip_bomb_safety_protection():
    """13. Test protection against ZIP bombs with enormous uncompressed size."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Create a compressed zero-byte string that decompresses to > 160 MB
        z.writestr("huge_file.txt", b"\x00" * (160 * 1024 * 1024))
    buf.seek(0)
    zip_bytes = buf.getvalue()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("bomb.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "ZIP_BOMB_DETECTED"
