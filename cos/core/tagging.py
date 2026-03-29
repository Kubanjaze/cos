"""COS metadata tagging system.

Adds flexible key-value tags to artifacts for retrieval by domain, source, and custom tags.
Completes Gate 1: ingest → normalize → store → tag → retrieve.

Usage:
    from cos.core.tagging import tag_artifact, search_artifacts
    tag_artifact(artifact_id, domain="cheminformatics", tags=["CETP", "inhibitor"])
    results = search_artifacts(domain="cheminformatics")
"""

import sqlite3
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.tagging")


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(settings.db_path)


def _init_tags_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artifact_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(artifact_id, key, value)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_key_value ON artifact_tags(key, value)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_artifact ON artifact_tags(artifact_id)")


def _artifact_exists(conn: sqlite3.Connection, artifact_id: str) -> bool:
    """Check if an artifact exists (by full or partial ID)."""
    row = conn.execute(
        "SELECT id FROM artifacts WHERE id = ? OR id LIKE ?",
        (artifact_id, artifact_id + "%"),
    ).fetchone()
    return row is not None


def _resolve_artifact_id(conn: sqlite3.Connection, partial_id: str) -> Optional[str]:
    """Resolve a partial artifact ID to full UUID."""
    row = conn.execute(
        "SELECT id FROM artifacts WHERE id = ? OR id LIKE ?",
        (partial_id, partial_id + "%"),
    ).fetchone()
    return row[0] if row else None


def tag_artifact(
    artifact_id: str,
    domain: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[list[str]] = None,
    description: Optional[str] = None,
    **extra_tags: str,
) -> int:
    """Add metadata tags to an artifact. Returns number of tags added."""
    conn = _get_conn()
    _init_tags_table(conn)

    # Resolve partial ID
    full_id = _resolve_artifact_id(conn, artifact_id)
    if not full_id:
        conn.close()
        raise ValueError(f"Artifact not found: {artifact_id}")

    count = 0

    def _insert(key: str, value: str):
        nonlocal count
        try:
            conn.execute(
                "INSERT OR IGNORE INTO artifact_tags (artifact_id, key, value) VALUES (?, ?, ?)",
                (full_id, key, value),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass  # duplicate tag

    if domain:
        _insert("domain", domain)
    if source:
        _insert("source", source)
    if description:
        _insert("description", description)
    if tags:
        for tag in tags:
            _insert("tag", tag.strip())
    for key, value in extra_tags.items():
        _insert(key, str(value))

    conn.commit()
    conn.close()

    logger.info(f"Tagged artifact {full_id[:8]}... with {count} tags", extra={"investigation_id": full_id[:8]})
    return count


def get_tags(artifact_id: str) -> dict[str, list[str]]:
    """Get all tags for an artifact, grouped by key."""
    conn = _get_conn()
    _init_tags_table(conn)
    full_id = _resolve_artifact_id(conn, artifact_id)
    if not full_id:
        conn.close()
        return {}

    rows = conn.execute(
        "SELECT key, value FROM artifact_tags WHERE artifact_id = ? ORDER BY key",
        (full_id,),
    ).fetchall()
    conn.close()

    result: dict[str, list[str]] = {}
    for key, value in rows:
        result.setdefault(key, []).append(value)
    return result


def search_artifacts(
    domain: Optional[str] = None,
    tag: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict]:
    """Search artifacts by metadata tags. Returns artifact records with their tags."""
    conn = _get_conn()
    _init_tags_table(conn)

    # Build query with tag filters
    conditions = []
    params = []

    if domain:
        conditions.append("a.id IN (SELECT artifact_id FROM artifact_tags WHERE key='domain' AND value=?)")
        params.append(domain)
    if tag:
        conditions.append("a.id IN (SELECT artifact_id FROM artifact_tags WHERE key='tag' AND value=?)")
        params.append(tag)
    if source:
        conditions.append("a.id IN (SELECT artifact_id FROM artifact_tags WHERE key='source' AND value LIKE ?)")
        params.append(f"%{source}%")

    where = " AND ".join(conditions) if conditions else "1=1"

    rows = conn.execute(
        f"SELECT a.id, a.type, a.uri, a.hash, a.created_at, a.investigation_id, a.size_bytes "
        f"FROM artifacts a WHERE {where} ORDER BY a.created_at DESC",
        params,
    ).fetchall()

    results = []
    for r in rows:
        artifact_id = r[0]
        tags = conn.execute(
            "SELECT key, value FROM artifact_tags WHERE artifact_id = ?", (artifact_id,)
        ).fetchall()
        tag_dict = {}
        for k, v in tags:
            tag_dict.setdefault(k, []).append(v)
        results.append({
            "id": artifact_id, "type": r[1], "uri": r[2], "hash": r[3][:12] + "...",
            "created_at": r[4], "investigation_id": r[5], "size_bytes": r[6],
            "tags": tag_dict,
        })

    conn.close()
    return results
