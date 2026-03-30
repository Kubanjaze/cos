"""COS episodic memory — records of what the system has done.

Episodic memory answers "what happened?" — pipeline runs, queries, analyses.
Distinct from semantic memory ("what do we know?") in Phase 127.

Usage:
    from cos.memory.episodic import episodic_memory
    episodic_memory.record("ingestion", "Ingested compounds.csv", input_summary="45 compounds",
                           output_summary="7 chunks", investigation_id="inv-001")
    episodes = episodic_memory.recall("inv-001")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.episodic")


@dataclass
class Episode:
    id: str
    episode_type: str
    description: str
    input_summary: str
    output_summary: str
    investigation_id: str
    duration_s: float
    cost_usd: float
    created_at: str


class EpisodicMemory:
    """Records of COS actions — episodic memory layer."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    episode_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    input_summary TEXT NOT NULL DEFAULT '',
                    output_summary TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    duration_s REAL NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_inv ON episodes(investigation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_type ON episodes(episode_type)")

    def record(
        self,
        episode_type: str,
        description: str,
        input_summary: str = "",
        output_summary: str = "",
        investigation_id: str = "default",
        duration_s: float = 0,
        cost_usd: float = 0,
    ) -> str:
        """Record an episode. Returns episode ID."""
        ep_id = f"ep-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO episodes (id, episode_type, description, input_summary, output_summary, "
                "investigation_id, duration_s, cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ep_id, episode_type, description, input_summary, output_summary,
                 investigation_id, duration_s, cost_usd, ts),
            )

        logger.info(f"Episode recorded: [{episode_type}] {description[:60]}",
                     extra={"investigation_id": investigation_id, "cost": cost_usd})
        return ep_id

    def recall(
        self,
        investigation_id: Optional[str] = None,
        episode_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[Episode]:
        """Recall episodes with optional filters."""
        conn = self._get_conn()
        conditions = []
        params = []
        if investigation_id:
            conditions.append("investigation_id=?")
            params.append(investigation_id)
        if episode_type:
            conditions.append("episode_type=?")
            params.append(episode_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"SELECT id, episode_type, description, input_summary, output_summary, "
            f"investigation_id, duration_s, cost_usd, created_at "
            f"FROM episodes WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [Episode(*r) for r in rows]

    def get_recent(self, limit: int = 10) -> list[Episode]:
        """Get most recent episodes across all investigations."""
        return self.recall(limit=limit)

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        total_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM episodes").fetchone()[0]
        by_type = conn.execute(
            "SELECT episode_type, COUNT(*) FROM episodes GROUP BY episode_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return {"total": total, "total_cost": round(total_cost, 6), "by_type": {t: c for t, c in by_type}}


# Singleton
episodic_memory = EpisodicMemory()
