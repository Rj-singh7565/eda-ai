"""
Storage Service — Abstracted File Storage supporting Local, AWS S3, and Supabase Storage.
"""

import os
from backend.app import config

# Optional S3 support via boto3
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    HAS_BOTO3 = False


class StorageService:
    def __init__(self):
        self.storage_type = config.STORAGE_TYPE
        if self.storage_type == "s3" and HAS_BOTO3:
            s3_kwargs = {}
            if config.S3_ENDPOINT_URL:
                s3_kwargs["endpoint_url"] = config.S3_ENDPOINT_URL
            if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
                s3_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
                s3_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
            self.s3_client = boto3.client("s3", **s3_kwargs)
        else:
            self.s3_client = None

    def save_upload_file(self, file_bytes: bytes, filename: str) -> str:
        """Save raw upload file and return storage path / URL."""
        if self.storage_type == "s3" and self.s3_client and config.S3_BUCKET:
            key = f"original/{filename}"
            self.s3_client.put_object(Bucket=config.S3_BUCKET, Key=key, Body=file_bytes)
            return f"s3://{config.S3_BUCKET}/{key}"
        
        # Local storage fallback
        local_path = os.path.join(config.UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return local_path

    def save_processed_markdown(self, doc_id: str, markdown_content: str) -> str:
        """Save normalized Markdown representation and return stored path."""
        filename = f"{doc_id}.md"
        if self.storage_type == "s3" and self.s3_client and config.S3_BUCKET:
            key = f"processed/{filename}"
            self.s3_client.put_object(
                Bucket=config.S3_BUCKET,
                Key=key,
                Body=markdown_content.encode("utf-8"),
                ContentType="text/markdown"
            )
            # Also save locally for fast retrieval
            local_path = os.path.join(config.PROCESSED_DIR, filename)
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            return local_path

        local_path = os.path.join(config.PROCESSED_DIR, filename)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return local_path

    def read_processed_markdown(self, doc_id: str, markdown_path: str = None) -> str:
        """Retrieve raw markdown text for a document."""
        if markdown_path and os.path.exists(markdown_path):
            with open(markdown_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        fallback_path = os.path.join(config.PROCESSED_DIR, f"{doc_id}.md")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if self.storage_type == "s3" and self.s3_client and config.S3_BUCKET:
            try:
                key = f"processed/{doc_id}.md"
                obj = self.s3_client.get_object(Bucket=config.S3_BUCKET, Key=key)
                return obj["Body"].read().decode("utf-8")
            except Exception:
                pass

        raise FileNotFoundError(f"Markdown representation not available for doc_id {doc_id}")

    def delete_document_files(self, doc_id: str):
        """Clean up storage resources associated with a document."""
        # Local upload cleanup
        try:
            for fname in os.listdir(config.UPLOAD_DIR):
                if fname.startswith(doc_id):
                    try:
                        os.remove(os.path.join(config.UPLOAD_DIR, fname))
                    except Exception:
                        pass
        except Exception:
            pass

        # Local processed markdown cleanup
        processed_path = os.path.join(config.PROCESSED_DIR, f"{doc_id}.md")
        if os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception:
                pass

        # Cloud storage cleanup
        if self.storage_type == "s3" and self.s3_client and config.S3_BUCKET:
            try:
                self.s3_client.delete_object(Bucket=config.S3_BUCKET, Key=f"processed/{doc_id}.md")
            except Exception:
                pass


storage_service = StorageService()
