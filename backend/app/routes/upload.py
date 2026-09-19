"""
Upload Route — File validation, streaming reception, ZIP archive unpacking,
magic byte detection, security validation, and background task dispatch.
"""

import os
import re
import uuid
import zipfile
import tempfile
import shutil
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.app import config
from backend.app.database import database
from backend.app.services import ingestion

router = APIRouter()

CHUNK_SIZE_BYTES = 64 * 1024  # 64 KB buffer for streaming disk writes
MAX_DECOMPRESSED_ZIP_BYTES = 150 * 1024 * 1024  # 150 MB zip bomb threshold


def is_safe_zip_path(target_path: str) -> bool:
    """
    Prevent Zip Slip / directory traversal vulnerabilities.
    Rejects paths with '..', leading slashes, backslashes, or drive letters.
    """
    clean_p = target_path.replace("\\", "/").strip()
    if clean_p.startswith("/") or bool(re.match(r"^[a-zA-Z]:", clean_p)):
        return False
    # Check for directory traversal components
    parts = clean_p.split("/")
    if any(part in ("..", "") for part in parts[:-1]):
        return False
    return ".." not in parts


@router.post("/upload")
@router.post("/api/documents/upload")
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a document (.pdf, .docx, .pptx, .xlsx, .csv, .txt, .md, images) or a .zip archive (up to 25MB).
    Streams upload to disk in chunks to avoid RAM duplication, validates format, unpacks ZIPs safely,
    and dispatches background ingestion tasks per file.
    """
    raw_filename = file.filename or "uploaded_file"
    original_filename = os.path.basename(raw_filename.replace("\\", "/"))
    if not original_filename or original_filename == ".":
        original_filename = "uploaded_file"
    ext = os.path.splitext(original_filename)[1].lower()

    # Step 1: Stream file from multipart request to disk in 64KB chunks
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext, dir=config.UPLOAD_DIR)
    file_size = 0

    try:
        with os.fdopen(temp_fd, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                file_size += len(chunk)
                f.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(
            status_code=500,
            content={"error": "UPLOAD_FAILED", "message": f"Failed to receive file stream: {str(e)}"}
        )

    # Step 2: Empty file validation
    if file_size == 0:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        err_code = "EMPTY_ZIP" if ext == ".zip" else "EMPTY_FILE"
        err_msg = "Uploaded ZIP archive is empty." if ext == ".zip" else "Uploaded file is empty (0 bytes)."
        return JSONResponse(
            status_code=400,
            content={"error": err_code, "message": err_msg}
        )

    # Step 3: Global File Size Limit (25 MB = 25 * 1024 * 1024 bytes)
    if file_size > config.MAX_FILE_SIZE_BYTES:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        err_code = "ZIP_TOO_LARGE" if ext == ".zip" else "FILE_TOO_LARGE"
        err_msg = (
            f"ZIP file exceeds the maximum allowed size of {config.MAX_FILE_SIZE_MB} MB."
            if ext == ".zip"
            else f"File size exceeds maximum limit of {config.MAX_FILE_SIZE_MB} MB."
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": err_code,
                "message": err_msg,
                "max_size_mb": config.MAX_FILE_SIZE_MB,
                "actual_size_mb": round(file_size / (1024 * 1024), 2)
            }
        )

    detected_type = ingestion.detect_file_type(temp_path)

    # ── BRANCH A: ZIP Archive Upload Flow ──────────────────────────────────
    if detected_type == "zip" or ext == ".zip":
        # Validate ZIP signature & structure
        if not zipfile.is_zipfile(temp_path):
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JSONResponse(
                status_code=400,
                content={"error": "INVALID_ZIP", "message": "Corrupted or invalid ZIP archive file."}
            )

        created_docs = []
        skipped_files = []
        seen_paths = set()

        try:
            with zipfile.ZipFile(temp_path, "r") as z:
                # Test archive integrity
                corrupt_entry = z.testzip()
                if corrupt_entry is not None:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "CORRUPTED_ENTRY",
                            "message": f"ZIP archive contains corrupted file entry: '{corrupt_entry}'."
                        }
                    )

                zip_entries = [info for info in z.infolist() if not info.is_dir()]

                if not zip_entries:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "EMPTY_ZIP", "message": "ZIP archive contains no files."}
                    )

                # Security: ZIP bomb detection (total uncompressed size check)
                total_uncompressed = sum(e.file_size for e in zip_entries)
                if total_uncompressed > MAX_DECOMPRESSED_ZIP_BYTES:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "ZIP_BOMB_DETECTED",
                            "message": f"Total uncompressed size ({round(total_uncompressed / (1024*1024), 1)} MB) exceeds safety threshold of 150 MB."
                        }
                    )

                for entry in zip_entries:
                    clean_entry_name = entry.filename.replace("\\", "/").strip("/")
                    raw_name = os.path.basename(clean_entry_name)

                    # Security: Zip Slip check
                    if not is_safe_zip_path(clean_entry_name):
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": "Path traversal / Zip Slip attempt rejected."
                        })
                        continue

                    # Filter out system and hidden files
                    if (
                        not raw_name
                        or raw_name.startswith(".")
                        or raw_name.startswith("._")
                        or "/." in clean_entry_name
                        or clean_entry_name.startswith("__MACOSX")
                        or "__MACOSX/" in clean_entry_name
                        or raw_name in ("Thumbs.db", ".DS_Store", "desktop.ini")
                    ):
                        continue

                    # Deduplicate entries
                    normalized_key = clean_entry_name.lower()
                    if normalized_key in seen_paths:
                        continue
                    seen_paths.add(normalized_key)

                    display_filename = clean_entry_name.replace("/", "_")
                    entry_ext = os.path.splitext(raw_name)[1].lower()

                    # Limit max files extracted per ZIP
                    if len(created_docs) >= config.MAX_ZIP_FILES:
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"Exceeded maximum ZIP limit of {config.MAX_ZIP_FILES} files."
                        })
                        continue

                    # Reject nested ZIP files
                    if entry_ext == ".zip":
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": "Nested ZIP archives are not supported."
                        })
                        continue

                    # Individual file size limit
                    if entry.file_size > config.MAX_FILE_SIZE_BYTES:
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"File size ({round(entry.file_size / (1024*1024), 1)} MB) exceeds maximum limit of {config.MAX_FILE_SIZE_MB} MB."
                        })
                        continue

                    # Stream extract entry in chunks to disk to avoid holding all entries in RAM
                    sub_temp_fd, sub_temp_path = tempfile.mkstemp(suffix=entry_ext, dir=config.UPLOAD_DIR)
                    try:
                        with z.open(entry) as source_f, os.fdopen(sub_temp_fd, "wb") as target_f:
                            shutil.copyfileobj(source_f, target_f, length=CHUNK_SIZE_BYTES)

                        sub_type = ingestion.detect_file_type(sub_temp_path)

                        if sub_type == "unknown" or sub_type == "zip":
                            if os.path.exists(sub_temp_path):
                                os.remove(sub_temp_path)
                            skipped_files.append({
                                "filename": raw_name,
                                "reason": f"Unsupported format '{entry_ext}'."
                            })
                            continue

                        doc_id = str(uuid.uuid4())
                        final_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}{entry_ext}")
                        os.replace(sub_temp_path, final_path)

                        doc_record = database.create_document(
                            doc_id, display_filename, entry.file_size, file_type=sub_type
                        )
                        background_tasks.add_task(
                            ingestion.run_ingestion_pipeline, doc_id, final_path, sub_type
                        )

                        created_docs.append({
                            "doc_id": doc_id,
                            "filename": display_filename,
                            "file_type": sub_type,
                            "status": "processing"
                        })
                    except Exception as extract_err:
                        if os.path.exists(sub_temp_path):
                            os.remove(sub_temp_path)
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"Extraction error: {str(extract_err)}"
                        })

        except zipfile.BadZipFile:
            return JSONResponse(
                status_code=400,
                content={"error": "INVALID_ZIP", "message": "Corrupted or invalid ZIP archive file."}
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if not created_docs and skipped_files:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "NO_VALID_DOCUMENTS",
                    "message": "No valid documents could be processed from ZIP archive.",
                    "skipped": skipped_files
                }
            )

        return {
            "batch": True,
            "documents": created_docs,
            "skipped": skipped_files,
            "message": f"ZIP uploaded. Ingestion initiated for {len(created_docs)} document(s)."
        }

    # ── BRANCH B: Single Document Upload Flow ──────────────────────────────
    if detected_type == "unknown":
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(
            status_code=400,
            content={
                "error": "UNSUPPORTED_FORMAT",
                "message": f"Unsupported or corrupted document format '{ext}'."
            }
        )

    doc_id = str(uuid.uuid4())
    final_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}{ext}")
    os.replace(temp_path, final_path)

    doc_record = database.create_document(doc_id, original_filename, file_size, file_type=detected_type)
    background_tasks.add_task(ingestion.run_ingestion_pipeline, doc_id, final_path, detected_type)

    return {
        "batch": False,
        "doc_id": doc_id,
        "filename": original_filename,
        "file_type": detected_type,
        "status": "processing",
        "documents": [doc_record],
        "skipped": [],
        "message": "Upload successful. Document ingestion initiated."
    }
