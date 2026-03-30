"""COS action generation engine — propose next actions. Phase 182.

Also covers: Phase 186 (priority ranking of actions).
"""

import sqlite3
import json
import time
import uuid
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.actions")


class ActionGenerator:
    """Generates and prioritizes possible actions from reasoning outputs."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proposed_actions (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL DEFAULT '',
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority REAL NOT NULL DEFAULT 0.5,
                    effort TEXT NOT NULL DEFAULT 'medium',
                    impact TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'proposed',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def generate(self, investigation_id: str = "default") -> list[dict]:
        """Generate actions from hypotheses, gaps, and insights."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        actions = []

        # Actions from hypotheses: "test hypothesis X"
        try:
            rows = conn.execute(
                "SELECT id, statement, confidence FROM hypotheses WHERE status='proposed' ORDER BY confidence DESC LIMIT 5"
            ).fetchall()
            for hid, stmt, conf in rows:
                aid = f"act-{uuid.uuid4().hex[:8]}"
                desc = f"Test hypothesis: {stmt[:80]}"
                priority = round(conf * 0.8, 3)
                conn.execute(
                    "INSERT OR IGNORE INTO proposed_actions (id, action_type, description, priority, effort, impact, status, investigation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (aid, "test_hypothesis", desc, priority, "medium", "high", "proposed", investigation_id, ts),
                )
                actions.append({"id": aid, "type": "test_hypothesis", "description": desc, "priority": priority})
        except Exception:
            pass

        # Actions from knowledge gaps: "fill gap in domain X"
        try:
            rows = conn.execute("SELECT domain, COUNT(*) FROM concepts GROUP BY domain HAVING COUNT(*) < 3").fetchall()
            for domain, cnt in rows:
                aid = f"act-{uuid.uuid4().hex[:8]}"
                desc = f"Expand knowledge in '{domain}' domain (only {cnt} concepts)"
                conn.execute(
                    "INSERT OR IGNORE INTO proposed_actions (id, action_type, description, priority, effort, impact, status, investigation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (aid, "fill_gap", desc, 0.6, "low", "medium", "proposed", investigation_id, ts),
                )
                actions.append({"id": aid, "type": "fill_gap", "description": desc, "priority": 0.6})
        except Exception:
            pass

        conn.commit()
        conn.close()

        # Phase 186: Priority ranking
        actions.sort(key=lambda x: x["priority"], reverse=True)
        for i, a in enumerate(actions):
            a["rank"] = i + 1

        logger.info(f"Generated {len(actions)} actions")
        return actions

    def list_actions(self, status: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT id, action_type, description, priority, effort, impact, status, created_at "
                "FROM proposed_actions WHERE status=? ORDER BY priority DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, action_type, description, priority, effort, impact, status, created_at "
                "FROM proposed_actions ORDER BY priority DESC"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "type": r[1], "description": r[2], "priority": r[3],
                 "effort": r[4], "impact": r[5], "status": r[6], "created_at": r[7]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM proposed_actions").fetchone()[0]
        by_type = conn.execute("SELECT action_type, COUNT(*) FROM proposed_actions GROUP BY action_type").fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


action_generator = ActionGenerator()
