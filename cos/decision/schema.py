"""COS decision object schema — the canonical Decision type. Phase 181.

Per Architect Notes: Decision has id, recommendation, actions[], evidence_refs[],
confidence, risks[], invalidation_conditions[].
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.schema")


@dataclass
class Decision:
    id: str
    title: str
    recommendation: str
    actions_json: str
    evidence_json: str
    confidence: float
    risks_json: str
    invalidation_json: str
    status: str
    investigation_id: str
    created_at: str
    updated_at: str

    @property
    def actions(self) -> list[dict]:
        return json.loads(self.actions_json)

    @property
    def risks(self) -> list[dict]:
        return json.loads(self.risks_json)

    @property
    def invalidation_conditions(self) -> list[str]:
        return json.loads(self.invalidation_json)


class DecisionStore:
    """Manages the canonical Decision objects."""

    _COLS = ("id, title, recommendation, actions_json, evidence_json, confidence, "
             "risks_json, invalidation_json, status, investigation_id, created_at, updated_at")

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    actions_json TEXT NOT NULL DEFAULT '[]',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    risks_json TEXT NOT NULL DEFAULT '[]',
                    invalidation_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'proposed',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dec_status ON decisions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dec_inv ON decisions(investigation_id)")

    def create(self, title: str, recommendation: str, actions: list[dict] = None,
               evidence: list[str] = None, confidence: float = 0.5,
               risks: list[dict] = None, invalidation_conditions: list[str] = None,
               investigation_id: str = "default") -> str:
        """Create a new decision. Returns decision ID."""
        did = f"dec-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                f"INSERT INTO decisions ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (did, title, recommendation, json.dumps(actions or []),
                 json.dumps(evidence or []), confidence, json.dumps(risks or []),
                 json.dumps(invalidation_conditions or []), "proposed", investigation_id, ts, ts),
            )
        logger.info(f"Decision created: {title} (conf={confidence:.2f})")
        return did

    def get(self, decision_id: str) -> Optional[Decision]:
        conn = self._get_conn()
        row = conn.execute(
            f"SELECT {self._COLS} FROM decisions WHERE id=? OR id LIKE ?",
            (decision_id, decision_id + "%"),
        ).fetchone()
        conn.close()
        return Decision(*row) if row else None

    def update_status(self, decision_id: str, status: str) -> bool:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("UPDATE decisions SET status=?, updated_at=? WHERE id=?",
                         (status, ts, decision_id))
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    def list_decisions(self, status: Optional[str] = None,
                       investigation_id: Optional[str] = None, limit: int = 50) -> list[Decision]:
        conn = self._get_conn()
        conditions, params = [], []
        if status:
            conditions.append("status=?")
            params.append(status)
        if investigation_id:
            conditions.append("investigation_id=?")
            params.append(investigation_id)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = conn.execute(
            f"SELECT {self._COLS} FROM decisions WHERE {where} ORDER BY confidence DESC LIMIT ?", params
        ).fetchall()
        conn.close()
        return [Decision(*r) for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        by_status = conn.execute("SELECT status, COUNT(*) FROM decisions GROUP BY status").fetchall()
        avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM decisions").fetchone()[0]
        conn.close()
        return {"total": total, "avg_confidence": round(avg_conf, 3),
                "by_status": {s: c for s, c in by_status}}


decision_store = DecisionStore()
