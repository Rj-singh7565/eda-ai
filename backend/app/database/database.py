"""
Database Layer — Supports PostgreSQL (DATABASE_URL) for production & SQLite for local development.
"""

import os
import sqlite3
from typing import List, Dict, Optional, Any
from backend.app import config

# Check for PostgreSQL connector availability
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False


def is_postgres() -> bool:
    return bool(config.DATABASE_URL and config.DATABASE_URL.startswith("postgres"))


def get_db_connection():
    """Create a connection to PostgreSQL if DATABASE_URL is set, else SQLite."""
    if is_postgres() and HAS_PSYCOPG2:
        conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_size BIGINT NOT NULL,
                        file_type VARCHAR(50) NOT NULL DEFAULT 'pdf',
                        page_count INT DEFAULT 0,
                        chunk_count INT DEFAULT 0,
                        status VARCHAR(50) NOT NULL DEFAULT 'processing',
                        error_message TEXT,
                        markdown_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id SERIAL PRIMARY KEY,
                        doc_id VARCHAR(255) NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        doc_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        file_type TEXT NOT NULL DEFAULT 'pdf',
                        page_count INTEGER DEFAULT 0,
                        chunk_count INTEGER DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'processing',
                        error_message TEXT,
                        markdown_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("PRAGMA table_info(documents)")
                columns = [col["name"] for col in cursor.fetchall()]
                if "file_type" not in columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN file_type TEXT NOT NULL DEFAULT 'pdf'")
                if "markdown_path" not in columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN markdown_path TEXT")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
    finally:
        conn.close()

# Ensure DB tables exist
init_db()


# ── Document CRUD Operations ──────────────────────────────────────────

def create_document(doc_id: str, filename: str, file_size: int, file_type: str = "pdf") -> Dict[str, Any]:
    """Register a new document with 'processing' status."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO documents (doc_id, filename, file_size, file_type, status)
                    VALUES (%s, %s, %s, %s, 'processing')
                """, (doc_id, filename, file_size, file_type))
                conn.commit()
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO documents (doc_id, filename, file_size, file_type, status)
                    VALUES (?, ?, ?, ?, 'processing')
                """, (doc_id, filename, file_size, file_type))
                conn.commit()
    finally:
        conn.close()
    return get_document(doc_id)


def update_document_status(
    doc_id: str,
    status: str,
    page_count: Optional[int] = None,
    chunk_count: Optional[int] = None,
    error_message: Optional[str] = None,
    markdown_path: Optional[str] = None
):
    """Update document ingestion status and stats."""
    conn = get_db_connection()
    try:
        placeholder = "%s" if (is_postgres() and HAS_PSYCOPG2) else "?"
        updates = [f"status = {placeholder}"]
        params = [status]

        if page_count is not None:
            updates.append(f"page_count = {placeholder}")
            params.append(page_count)

        if chunk_count is not None:
            updates.append(f"chunk_count = {placeholder}")
            params.append(chunk_count)

        if error_message is not None:
            updates.append(f"error_message = {placeholder}")
            params.append(error_message)

        if markdown_path is not None:
            updates.append(f"markdown_path = {placeholder}")
            params.append(markdown_path)

        params.append(doc_id)
        query = f"UPDATE documents SET {', '.join(updates)} WHERE doc_id = {placeholder}"

        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                conn.commit()
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                conn.commit()
    finally:
        conn.close()


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve document details by doc_id."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    finally:
        conn.close()


def list_documents() -> List[Dict[str, Any]]:
    """Retrieve all registered documents sorted by upload date descending."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_document(doc_id: str) -> bool:
    """Delete document and its chat history."""
    conn = get_db_connection()
    deleted = False
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM chat_history WHERE doc_id = %s", (doc_id,))
                cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chat_history WHERE doc_id = ?", (doc_id,))
                cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
    finally:
        conn.close()
    return deleted


# ── Chat History Operations ───────────────────────────────────────────

def add_chat_turn(doc_id: str, question: str, answer: str):
    """Record a Q&A exchange for a document session."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO chat_history (doc_id, question, answer)
                    VALUES (%s, %s, %s)
                """, (doc_id, question, answer))
                conn.commit()
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_history (doc_id, question, answer)
                    VALUES (?, ?, ?)
                """, (doc_id, question, answer))
                conn.commit()
    finally:
        conn.close()


def get_recent_chat_history(doc_id: str, limit: int = config.MEMORY_TURNS) -> List[Dict[str, str]]:
    """Fetch recent Q&A turns for inclusion in LLM prompt context."""
    conn = get_db_connection()
    try:
        if is_postgres() and HAS_PSYCOPG2:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT question, answer FROM chat_history
                    WHERE doc_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                """, (doc_id, limit))
                rows = cursor.fetchall()
                history = [dict(row) for row in reversed(rows)]
                return history
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT question, answer FROM chat_history
                    WHERE doc_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (doc_id, limit))
                rows = cursor.fetchall()
                history = [dict(row) for row in reversed(rows)]
                return history
    finally:
        conn.close()
