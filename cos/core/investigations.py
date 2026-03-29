"""COS investigation state manager.

Investigation is the primary unit of work (ADR-003).
Manages lifecycle: created → active → completed | archived.

Usage:
    from cos.core.investigations import investigation_manager
    inv_id = investigation_manager.create("What drives KRAS potency?", domain="cheminformatics")
    investigation_manager.activate(inv_id)
    detail = investigation_manager.get(inv_id)
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.investigations")

VALID_TRANSITIONS = {
    "created": {"active"},
    "active": {"completed", "archived"},
    "completed": {"archived"},
    "archived": set(),
}


@dataclass
class Investigation:
    id: str
    title: str
    domain: str
    status: str
    created_at: str
    updated_at: str
    tags: str
    notes: str


class InvestigationManager:
    """Lifecycle manager for COS investigations."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'created',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_status ON investigations(status)")

    def create(
        self,
        title: str,
        domain: str = "",
        tags: str = "",
        notes: str = "",
    ) -> str:
        """Create a new investigation. Returns investigation ID."""
        inv_id = f"inv-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO investigations (id, title, domain, status, created_at, updated_at, tags, notes) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?)",
                (inv_id, title, domain, ts, ts, tags, notes),
            )
        logger.info(f"Investigation created: {inv_id} — '{title}'")
        return inv_id

    def _transition(self, inv_id: str, new_status: str):
        """Transition investigation to new status with validation."""
        conn = self._get_conn()
        row = conn.execute("SELECT status FROM investigations WHERE id=?", (inv_id,)).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Investigation not found: {inv_id}")

        current = row[0]
        if new_status not in VALID_TRANSITIONS.get(current, set()):
            conn.close()
            raise ValueError(f"Invalid transition: {current} → {new_status}")

        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute("UPDATE investigations SET status=?, updated_at=? WHERE id=?", (new_status, ts, inv_id))
        conn.commit()
        conn.close()
        logger.info(f"Investigation {inv_id}: {current} → {new_status}")

    def activate(self, inv_id: str):
        self._transition(inv_id, "active")

    def complete(self, inv_id: str):
        self._transition(inv_id, "completed")

    def archive(self, inv_id: str):
        self._transition(inv_id, "archived")

    def get(self, inv_id: str) -> Optional[dict]:
        """Get full investigation detail with cross-table aggregation."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM investigations WHERE id=?", (inv_id,)).fetchone()
        if not row:
            conn.close()
            return None

        inv = Investigation(*row)

        # Cross-table aggregation
        artifact_count = conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE investigation_id=?", (inv_id,)
        ).fetchone()[0]

        version_count = conn.execute(
            "SELECT COUNT(*) FROM versions WHERE investigation_id=?", (inv_id,)
        ).fetchone()[0]

        total_cost = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events WHERE investigation_id=?", (inv_id,)
        ).fetchone()[0]

        conn.close()

        return {
            "id": inv.id, "title": inv.title, "domain": inv.domain,
            "status": inv.status, "created_at": inv.created_at, "updated_at": inv.updated_at,
            "tags": inv.tags, "notes": inv.notes,
            "artifacts": artifact_count, "versions": version_count,
            "total_cost": round(total_cost, 6),
        }

    def list_investigations(self, status: Optional[str] = None) -> list[dict]:
        """List investigations, optionally filtered by status."""
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT id, title, domain, status, created_at FROM investigations WHERE status=? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, domain, status, created_at FROM investigations ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "domain": r[2], "status": r[3], "created_at": r[4]} for r in rows]


# Singleton
investigation_manager = InvestigationManager()
