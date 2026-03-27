"""COS file ingestion service.

Normalizes PDF, CSV, and TXT inputs into a common document format.
Stores artifacts with content-addressable hashing (SHA-256).

Usage:
    from cos.core.ingestion import ingest_file
    artifact = ingest_file("data/compounds.csv", investigation_id="inv-001")
"""

import hashlib
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.ingestion")


@dataclass
class Artifact:
    """Artifact record — per Architect Notes schema."""
    id: str
    type: str  # file type: txt, csv, pdf
    uri: str  # original file path
    hash: str  # SHA-256 of normalized content
    schema_version: str
    created_at: str
    investigation_id: str
    size_bytes: int
    stored_path: str  # path to normalized text


# ── File type handlers ──────────────────────────────────────────────────

def _extract_txt(path: str) -> str:
    """Read plain text file."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _extract_csv(path: str) -> str:
    """Read CSV and convert to markdown table string."""
    import pandas as pd
    df = pd.read_csv(path)
    return df.to_markdown(index=False)


def _extract_pdf(path: str) -> str:
    """Extract text from PDF. Requires pdfplumber (optional dep)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not installed — reading PDF as raw text")
        return Path(path).read_text(encoding="utf-8", errors="replace")


HANDLERS = {
    ".txt": _extract_txt,
    ".csv": _extract_csv,
    ".pdf": _extract_pdf,
    ".md": _extract_txt,
    ".json": _extract_txt,
}


# ── Storage ─────────────────────────────────────────────────────────────

def _get_artifacts_dir() -> Path:
    """Get or create the artifacts storage directory."""
    artifacts_dir = Path(settings.storage_dir) / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def _init_artifacts_table(conn: sqlite3.Connection):
    """Create artifacts table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            uri TEXT NOT NULL,
            hash TEXT NOT NULL,
            schema_version TEXT NOT NULL DEFAULT '1.0',
            created_at TEXT NOT NULL,
            investigation_id TEXT NOT NULL DEFAULT 'default',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            stored_path TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_investigation ON artifacts(investigation_id)")


# ── Public API ──────────────────────────────────────────────────────────

def ingest_file(
    file_path: str,
    investigation_id: str = "default",
) -> Artifact:
    """Ingest a file into COS. Returns the Artifact record."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    handler = HANDLERS.get(ext)
    if handler is None:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(HANDLERS.keys())}")

    # Extract text
    logger.info(f"Ingesting {path.name} ({ext})", extra={"investigation_id": investigation_id})
    content = handler(str(path))
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Content-addressable storage
    artifacts_dir = _get_artifacts_dir()
    stored_path = artifacts_dir / f"{content_hash}.txt"

    # Check for duplicate
    db_path = settings.db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    _init_artifacts_table(conn)

    existing = conn.execute("SELECT id FROM artifacts WHERE hash = ?", (content_hash,)).fetchone()
    if existing:
        logger.info(f"Duplicate detected (hash={content_hash[:12]}...) — skipping write, returning existing artifact")
        row = conn.execute("SELECT * FROM artifacts WHERE hash = ?", (content_hash,)).fetchone()
        conn.close()
        return Artifact(
            id=row[0], type=row[1], uri=row[2], hash=row[3],
            schema_version=row[4], created_at=row[5], investigation_id=row[6],
            size_bytes=row[7], stored_path=row[8],
        )

    # Store content
    stored_path.write_text(content, encoding="utf-8")

    # Create artifact record
    artifact = Artifact(
        id=str(uuid.uuid4()),
        type=ext.lstrip("."),
        uri=str(path.resolve()),
        hash=content_hash,
        schema_version="1.0",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        investigation_id=investigation_id,
        size_bytes=len(content.encode("utf-8")),
        stored_path=str(stored_path),
    )

    conn.execute(
        "INSERT INTO artifacts (id, type, uri, hash, schema_version, created_at, investigation_id, size_bytes, stored_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (artifact.id, artifact.type, artifact.uri, artifact.hash, artifact.schema_version,
         artifact.created_at, artifact.investigation_id, artifact.size_bytes, artifact.stored_path),
    )
    conn.commit()
    conn.close()

    logger.info(
        f"Ingested: {path.name} → {content_hash[:12]}... ({artifact.size_bytes} bytes)",
        extra={"investigation_id": investigation_id},
    )
    return artifact


def list_artifacts(investigation_id: Optional[str] = None) -> list[dict]:
    """List all artifacts, optionally filtered by investigation."""
    conn = sqlite3.connect(settings.db_path)
    _init_artifacts_table(conn)
    if investigation_id:
        rows = conn.execute(
            "SELECT id, type, uri, hash, created_at, investigation_id, size_bytes FROM artifacts WHERE investigation_id = ? ORDER BY created_at DESC",
            (investigation_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, type, uri, hash, created_at, investigation_id, size_bytes FROM artifacts ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [
        {"id": r[0], "type": r[1], "uri": r[2], "hash": r[3][:12] + "...",
         "created_at": r[4], "investigation_id": r[5], "size_bytes": r[6]}
        for r in rows
    ]
