"""COS versioning system for outputs and runs.

Tracks per-investigation version numbers so outputs are versioned, not overwritten.

Usage:
    from cos.core.versioning import version_manager
    v = version_manager.stamp("inv-001", artifact_id="abc-123", description="Initial ingestion")
    print(v)  # 1
    versions = version_manager.get_versions("inv-001")
"""

import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.versioning")


@dataclass
class Version:
    id: int
    investigation_id: str
    version_number: int
    artifact_id: Optional[str]
    created_at: str
    description: str


class VersionManager:
    """Per-investigation version tracking."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    artifact_id TEXT,
                    created_at TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_investigation ON versions(investigation_id)")

    def next_version(self, investigation_id: str) -> int:
        """Get the next version number for an investigation."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(version_number) FROM versions WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
        conn.close()
        current = row[0] if row[0] is not None else 0
        return current + 1

    def stamp(
        self,
        investigation_id: str,
        artifact_id: Optional[str] = None,
        description: str = "",
    ) -> int:
        """Create a new version record. Returns the version number."""
        version_num = self.next_version(investigation_id)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO versions (investigation_id, version_number, artifact_id, created_at, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (investigation_id, version_num, artifact_id, ts, description),
            )

        logger.info(
            f"Version {version_num} stamped for {investigation_id}",
            extra={"investigation_id": investigation_id},
        )
        return version_num

    def get_versions(self, investigation_id: str) -> list[Version]:
        """Get all versions for an investigation, ordered by version number."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, investigation_id, version_number, artifact_id, created_at, description "
            "FROM versions WHERE investigation_id = ? ORDER BY version_number",
            (investigation_id,),
        ).fetchall()
        conn.close()
        return [Version(*r) for r in rows]

    def get_latest(self, investigation_id: str) -> Optional[Version]:
        """Get the most recent version for an investigation."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, investigation_id, version_number, artifact_id, created_at, description "
            "FROM versions WHERE investigation_id = ? ORDER BY version_number DESC LIMIT 1",
            (investigation_id,),
        ).fetchone()
        conn.close()
        return Version(*row) if row else None


# Singleton
version_manager = VersionManager()
