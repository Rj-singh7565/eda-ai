"""
Upload Route — File validation, ZIP archive unpacking, magic byte detection, and background task dispatch.
"""

import os
import uuid
import zipfile
import tempfile
from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.app import config
from backend.app.database import database
from backend.app.services import ingestion

router = APIRouter()


@router.post("/upload")
@router.post("/api/documents/upload")
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a document (.pdf, .docx, .pptx, .xlsx, .csv, .txt, .md, images) or a .zip archive.
    Validates format via magic byte signatures, processes ZIP archives, registers DB metadata,
    and dispatches background ingestion tasks per file.
    """
    raw_filename = file.filename or "uploaded_file"
    original_filename = os.path.basename(raw_filename.replace("\\", "/"))
    if not original_filename or original_filename == ".":
        original_filename = "uploaded_file"
    ext = os.path.splitext(original_filename)[1].lower()

    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        return JSONResponse(
            status_code=400,
            content={"message": "Uploaded file is empty."}
        )

    # Save to temporary file for format detection
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext, dir=config.UPLOAD_DIR)
    try:
        with os.fdopen(temp_fd, "wb") as f:
            f.write(contents)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Failed to receive file: {str(e)}"}
        )

    detected_type = ingestion.detect_file_type(temp_path)

    # Reject unsupported formats
    if detected_type == "unknown":
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(
            status_code=400,
            content={"message": f"Unsupported or corrupted document format '{ext}'."}
        )

    # ── ZIP Archive Upload Flow ─────────────────────────────────────────
    if detected_type == "zip":
        if not zipfile.is_zipfile(temp_path):
            os.remove(temp_path)
            return JSONResponse(
                status_code=400,
                content={"message": "Corrupted or invalid ZIP archive file."}
            )

        created_docs = []
        skipped_files = []
        seen_paths = set()

        try:
            with zipfile.ZipFile(temp_path, "r") as z:
                zip_entries = [info for info in z.infolist() if not info.is_dir()]

                for entry in zip_entries:
                    clean_entry_name = entry.filename.replace("\\", "/").strip("/")
                    raw_name = os.path.basename(clean_entry_name)
                    if not raw_name or raw_name.startswith(".") or raw_name.startswith("._") or "/." in clean_entry_name or clean_entry_name.startswith("__MACOSX") or "__MACOSX/" in clean_entry_name or raw_name in ("Thumbs.db", ".DS_Store", "desktop.ini"):
                        continue

                    # Deduplicate duplicate ZIP archive entries
                    normalized_key = clean_entry_name.lower()
                    if normalized_key in seen_paths:
                        continue
                    seen_paths.add(normalized_key)

                    # If in subfolder, prefix with folder name for clarity (e.g. data_report.pdf)
                    display_filename = clean_entry_name.replace("/", "_")
                    entry_ext = os.path.splitext(raw_name)[1].lower()

                    if len(created_docs) >= config.MAX_ZIP_FILES:
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"Exceeded maximum ZIP limit of {config.MAX_ZIP_FILES} files."
                        })
                        continue

                    if entry_ext == ".zip":
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": "Nested ZIP archives are not supported."
                        })
                        continue

                    if entry.file_size > config.MAX_FILE_SIZE_BYTES:
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"File size exceeds maximum limit of {config.MAX_FILE_SIZE_MB}MB."
                        })
                        continue

                    entry_data = z.read(entry.filename)
                    sub_temp_fd, sub_temp_path = tempfile.mkstemp(suffix=entry_ext, dir=config.UPLOAD_DIR)
                    with os.fdopen(sub_temp_fd, "wb") as sf:
                        sf.write(entry_data)

                    sub_type = ingestion.detect_file_type(sub_temp_path)

                    if sub_type == "unknown" or sub_type == "zip":
                        os.remove(sub_temp_path)
                        skipped_files.append({
                            "filename": raw_name,
                            "reason": f"Unsupported format '{entry_ext}'."
                        })
                        continue

                    doc_id = str(uuid.uuid4())
                    final_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}{entry_ext}")
                    os.replace(sub_temp_path, final_path)

                    doc_record = database.create_document(doc_id, display_filename, entry.file_size, file_type=sub_type)
                    background_tasks.add_task(ingestion.run_ingestion_pipeline, doc_id, final_path, sub_type)

                    created_docs.append({
                        "doc_id": doc_id,
                        "filename": display_filename,
                        "file_type": sub_type,
                        "status": "processing"
                    })

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if not created_docs and skipped_files:
            return JSONResponse(
                status_code=400,
                content={
                    "message": "No valid documents found in ZIP archive.",
                    "skipped": skipped_files
                }
            )

        return {
            "batch": True,
            "documents": created_docs,
            "skipped": skipped_files,
            "message": f"ZIP uploaded. Ingestion initiated for {len(created_docs)} document(s)."
        }

    # ── Single Document Upload Flow ─────────────────────────────────────
    if file_size > config.MAX_FILE_SIZE_BYTES:
        os.remove(temp_path)
        return JSONResponse(
            status_code=400,
            content={"message": f"File size exceeds limit of {config.MAX_FILE_SIZE_MB}MB."}
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
