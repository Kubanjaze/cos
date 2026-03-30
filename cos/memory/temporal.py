"""COS temporal tagging — time-aware memory.

Adds temporal context to entities, documents, and relations.

Usage:
    from cos.memory.temporal import temporal_tagger
    temporal_tagger.tag("entity", "ent-abc123", "Q1 2026 assay data", time_point="2026-03-15")
    timeline = temporal_tagger.get_timeline("inv-001")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.temporal")


@dataclass
class TemporalTag:
    id: str
    target_type: str
    target_id: str
    time_context: str
    time_point: Optional[str]
    investigation_id: str
    created_at: str


class TemporalTagger:
    """Time-aware memory annotations."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_tags (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    time_context TEXT NOT NULL,
                    time_point TEXT,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_target ON temporal_tags(target_type, target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_inv ON temporal_tags(investigation_id)")

    def tag(
        self,
        target_type: str,
        target_id: str,
        time_context: str,
        time_point: Optional[str] = None,
        investigation_id: str = "default",
    ) -> str:
        """Add a temporal annotation. Returns tag ID."""
        tag_id = f"tmp-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO temporal_tags (id, target_type, target_id, time_context, time_point, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tag_id, target_type, target_id, time_context, time_point, investigation_id, ts),
            )

        logger.info(f"Temporal tag: {target_type}/{target_id[:12]} — '{time_context}'",
                     extra={"investigation_id": investigation_id})
        return tag_id

    def get_tags(self, target_type: str, target_id: str) -> list[TemporalTag]:
        """Get temporal tags for a specific target."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, target_type, target_id, time_context, time_point, investigation_id, created_at "
            "FROM temporal_tags WHERE target_type=? AND (target_id=? OR target_id LIKE ?) "
            "ORDER BY created_at",
            (target_type, target_id, target_id + "%"),
        ).fetchall()
        conn.close()
        return [TemporalTag(*r) for r in rows]

    def get_timeline(self, investigation_id: str) -> list[dict]:
        """Get ordered timeline of all temporal events for an investigation."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, target_type, target_id, time_context, time_point, created_at "
            "FROM temporal_tags WHERE investigation_id=? "
            "ORDER BY COALESCE(time_point, created_at)",
            (investigation_id,),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "target_type": r[1], "target_id": r[2],
             "time_context": r[3], "time_point": r[4], "created_at": r[5]}
            for r in rows
        ]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM temporal_tags").fetchone()[0]
        by_type = conn.execute(
            "SELECT target_type, COUNT(*) FROM temporal_tags GROUP BY target_type"
        ).fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


# Singleton
temporal_tagger = TemporalTagger()
