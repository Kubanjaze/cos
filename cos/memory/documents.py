"""COS document store — raw + parsed text with chunking.

Persists documents as metadata + text chunks for retrieval and embedding.

Usage:
    from cos.memory.documents import document_store
    doc_id = document_store.store_document(artifact_id="abc-123", investigation_id="inv-001")
    chunks = document_store.get_chunks(doc_id)
"""

import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.documents")

DEFAULT_MAX_CHUNK_SIZE = 500  # chars


@dataclass
class Document:
    id: str
    artifact_id: str
    title: str
    source_path: str
    char_count: int
    chunk_count: int
    investigation_id: str
    created_at: str


@dataclass
class Chunk:
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    char_count: int


def _chunk_text(text: str, max_size: int = DEFAULT_MAX_CHUNK_SIZE) -> list[str]:
    """Split text into chunks by paragraph, merging small ones."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text[:max_size]] if text.strip() else []

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # If single paragraph exceeds max, split by sentences
            if len(para) > max_size:
                while para:
                    chunks.append(para[:max_size])
                    para = para[max_size:]
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


class DocumentStore:
    """Persistent document + chunk storage."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_investigation ON documents(investigation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_artifact ON documents(artifact_id)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    char_count INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)")

    def store_document(
        self,
        artifact_id: str,
        investigation_id: str = "default",
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    ) -> str:
        """Store a document from an artifact. Returns document ID."""
        conn = self._get_conn()

        # Load artifact
        row = conn.execute(
            "SELECT uri, stored_path FROM artifacts WHERE id=? OR id LIKE ?",
            (artifact_id, artifact_id + "%"),
        ).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Artifact not found: {artifact_id}")

        uri, stored_path = row

        # Read text from stored artifact
        text = Path(stored_path).read_text(encoding="utf-8", errors="replace")
        title = Path(uri).stem

        # Chunk
        chunks = _chunk_text(text, max_chunk_size)

        # Create document record
        doc_id = f"doc-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        conn.execute(
            "INSERT INTO documents (id, artifact_id, title, source_path, char_count, chunk_count, investigation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, artifact_id, title, stored_path, len(text), len(chunks), investigation_id, ts),
        )

        # Store chunks
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"chk-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, chunk_index, chunk_text, char_count) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, i, chunk_text, len(chunk_text)),
            )

        conn.commit()
        conn.close()

        logger.info(f"Document stored: {doc_id} ({len(chunks)} chunks, {len(text)} chars)",
                     extra={"investigation_id": investigation_id})
        return doc_id

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document metadata."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, artifact_id, title, source_path, char_count, chunk_count, investigation_id, created_at "
            "FROM documents WHERE id=? OR id LIKE ?",
            (doc_id, doc_id + "%"),
        ).fetchone()
        conn.close()
        return Document(*row) if row else None

    def get_chunks(self, doc_id: str) -> list[Chunk]:
        """Get all chunks for a document, ordered by index."""
        conn = self._get_conn()
        # Resolve partial ID
        full_id = conn.execute("SELECT id FROM documents WHERE id=? OR id LIKE ?", (doc_id, doc_id + "%")).fetchone()
        if not full_id:
            conn.close()
            return []
        rows = conn.execute(
            "SELECT id, document_id, chunk_index, chunk_text, char_count FROM document_chunks WHERE document_id=? ORDER BY chunk_index",
            (full_id[0],),
        ).fetchall()
        conn.close()
        return [Chunk(*r) for r in rows]

    def search_text(self, query: str, investigation_id: Optional[str] = None) -> list[dict]:
        """Search chunks for text substring. Returns matching chunks with document info."""
        conn = self._get_conn()
        if investigation_id:
            rows = conn.execute(
                "SELECT c.chunk_text, c.chunk_index, d.id, d.title, d.investigation_id "
                "FROM document_chunks c JOIN documents d ON c.document_id = d.id "
                "WHERE c.chunk_text LIKE ? AND d.investigation_id = ? "
                "ORDER BY d.created_at DESC LIMIT 20",
                (f"%{query}%", investigation_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT c.chunk_text, c.chunk_index, d.id, d.title, d.investigation_id "
                "FROM document_chunks c JOIN documents d ON c.document_id = d.id "
                "WHERE c.chunk_text LIKE ? ORDER BY d.created_at DESC LIMIT 20",
                (f"%{query}%",),
            ).fetchall()
        conn.close()
        return [
            {"text": r[0][:200], "chunk_index": r[1], "doc_id": r[2], "title": r[3], "investigation_id": r[4]}
            for r in rows
        ]

    def list_documents(self, investigation_id: Optional[str] = None) -> list[Document]:
        """List all documents."""
        conn = self._get_conn()
        if investigation_id:
            rows = conn.execute(
                "SELECT id, artifact_id, title, source_path, char_count, chunk_count, investigation_id, created_at "
                "FROM documents WHERE investigation_id=? ORDER BY created_at DESC",
                (investigation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, artifact_id, title, source_path, char_count, chunk_count, investigation_id, created_at "
                "FROM documents ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [Document(*r) for r in rows]


# Singleton
document_store = DocumentStore()
