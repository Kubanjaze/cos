"""COS memory snapshot system — freeze memory state at a point in time.

Usage:
    from cos.memory.snapshots import snapshot_manager
    sid = snapshot_manager.create("pre-analysis", investigation_id="inv-001")
    snapshots = snapshot_manager.list_snapshots()
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.snapshots")


@dataclass
class Snapshot:
    id: str
    name: str
    description: str
    investigation_id: str
    snapshot_data: str
    created_at: str


class SnapshotManager:
    """Creates and manages memory state snapshots."""

    _COLS = "id, name, description, investigation_id, snapshot_data, created_at"

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_snapshots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    snapshot_data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_inv ON memory_snapshots(investigation_id)")

    def create(self, name: str, description: str = "",
               investigation_id: str = "default") -> str:
        """Create a snapshot of current memory state. Returns snapshot ID."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        data = {
            "timestamp": ts,
            "counts": self._gather_counts(conn),
            "concepts": self._gather_concepts(conn),
            "entities_summary": self._gather_entity_summary(conn),
            "relations_count": self._safe_count(conn, "entity_relations"),
            "episodes_count": self._safe_count(conn, "episodes"),
            "conflicts_count": self._safe_count(conn, "conflicts"),
        }

        sid = f"snap-{uuid.uuid4().hex[:8]}"
        conn.execute(
            f"INSERT INTO memory_snapshots ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?)",
            (sid, name, description, investigation_id, json.dumps(data), ts),
        )
        conn.commit()
        conn.close()

        logger.info(f"Snapshot created: {name} ({sid})")
        return sid

    def _gather_counts(self, conn) -> dict:
        tables = ["documents", "document_chunks", "entities", "entity_relations",
                   "concepts", "episodes", "procedures", "conflicts", "provenance"]
        counts = {}
        for t in tables:
            counts[t] = self._safe_count(conn, t)
        return counts

    def _safe_count(self, conn, table) -> int:
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0

    def _gather_concepts(self, conn) -> list[dict]:
        try:
            rows = conn.execute(
                "SELECT name, domain, confidence FROM concepts ORDER BY confidence DESC LIMIT 20"
            ).fetchall()
            return [{"name": n, "domain": d, "confidence": c} for n, d, c in rows]
        except Exception:
            return []

    def _gather_entity_summary(self, conn) -> dict:
        try:
            rows = conn.execute(
                "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type"
            ).fetchall()
            return {t: c for t, c in rows}
        except Exception:
            return {}

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        conn = self._get_conn()
        row = conn.execute(
            f"SELECT {self._COLS} FROM memory_snapshots WHERE id=? OR id LIKE ?",
            (snapshot_id, snapshot_id + "%"),
        ).fetchone()
        conn.close()
        return Snapshot(*row) if row else None

    def list_snapshots(self, investigation_id: Optional[str] = None) -> list[Snapshot]:
        conn = self._get_conn()
        if investigation_id:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_snapshots WHERE investigation_id=? ORDER BY created_at DESC",
                (investigation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_snapshots ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [Snapshot(*r) for r in rows]

    def compare(self, snap_a_id: str, snap_b_id: str) -> dict:
        """Compare two snapshots."""
        a = self.get(snap_a_id)
        b = self.get(snap_b_id)
        if not a or not b:
            return {"error": "Snapshot not found"}

        data_a = json.loads(a.snapshot_data)
        data_b = json.loads(b.snapshot_data)

        diffs = {}
        for table, count_a in data_a.get("counts", {}).items():
            count_b = data_b.get("counts", {}).get(table, 0)
            if count_a != count_b:
                diffs[table] = {"before": count_a, "after": count_b, "delta": count_b - count_a}

        return {"snapshot_a": a.name, "snapshot_b": b.name, "diffs": diffs}

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memory_snapshots").fetchone()[0]
        conn.close()
        return {"total_snapshots": total}


# Singleton
snapshot_manager = SnapshotManager()
