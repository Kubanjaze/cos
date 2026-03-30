"""COS incremental memory updates — continuous memory evolution.

Tracks changes to memory items and applies incremental updates rather than
full recomputation.

Usage:
    from cos.memory.incremental import update_tracker
    update_tracker.record_change("concept", "con-abc", "update", {"field": "confidence", "old": 0.5, "new": 0.9})
    pending = update_tracker.get_pending()
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.incremental")


@dataclass
class MemoryChange:
    id: str
    target_type: str
    target_id: str
    change_type: str
    change_data: str
    status: str
    investigation_id: str
    created_at: str
    applied_at: str


class IncrementalUpdateTracker:
    """Tracks and manages incremental memory updates."""

    _COLS = "id, target_type, target_id, change_type, change_data, status, investigation_id, created_at, applied_at"

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_changes (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    change_data TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mc_status ON memory_changes(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mc_type ON memory_changes(target_type)")

    def record_change(self, target_type: str, target_id: str, change_type: str,
                      change_data: Optional[dict] = None,
                      investigation_id: str = "default") -> str:
        """Record a memory change. Returns change ID."""
        cid = f"chg-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                f"INSERT INTO memory_changes ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, target_type, target_id, change_type,
                 json.dumps(change_data or {}), "pending", investigation_id, ts, ""),
            )
        logger.info(f"Change recorded: {change_type} on {target_type}/{target_id[:12]}")
        return cid

    def get_pending(self, target_type: Optional[str] = None) -> list[MemoryChange]:
        """Get pending changes."""
        conn = self._get_conn()
        if target_type:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_changes WHERE status='pending' AND target_type=? ORDER BY created_at",
                (target_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_changes WHERE status='pending' ORDER BY created_at"
            ).fetchall()
        conn.close()
        return [MemoryChange(*r) for r in rows]

    def mark_applied(self, change_id: str) -> bool:
        """Mark a change as applied."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memory_changes SET status='applied', applied_at=? WHERE id=?",
                (ts, change_id),
            )
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    def apply_pending(self) -> int:
        """Apply all pending changes (mark as applied). Returns count."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memory_changes SET status='applied', applied_at=? WHERE status='pending'",
                (ts,),
            )
            applied = conn.execute("SELECT changes()").fetchone()[0]
        logger.info(f"Applied {applied} pending changes")
        return applied

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memory_changes").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) FROM memory_changes GROUP BY status"
        ).fetchall()
        by_type = conn.execute(
            "SELECT change_type, COUNT(*) FROM memory_changes GROUP BY change_type"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "by_status": {s: c for s, c in by_status},
            "by_type": {t: c for t, c in by_type},
        }


# Singleton
update_tracker = IncrementalUpdateTracker()
