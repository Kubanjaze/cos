"""COS causal inference scaffolding — identify what drives what.

Phase 149: Builds causal relationship candidates from correlation patterns.
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.causal")


class CausalInference:
    """Identifies potential causal relationships."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS causal_claims (
                    id TEXT PRIMARY KEY,
                    cause TEXT NOT NULL,
                    effect TEXT NOT NULL,
                    mechanism TEXT NOT NULL DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.3,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def infer(self, investigation_id: str = "default") -> list[dict]:
        """Infer causal relationships from scaffold-activity patterns."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        claims = []

        # Scaffold → activity causal candidates
        rows = conn.execute("""
            SELECT r1.target_value as scaffold, COUNT(DISTINCT r2.source_entity) as active_count
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
            GROUP BY r1.target_value HAVING active_count >= 2
        """).fetchall()

        for scaffold, count in rows:
            cid = f"csl-{uuid.uuid4().hex[:8]}"
            conf = min(0.6, 0.3 + count * 0.03)
            claim = {
                "id": cid, "cause": f"scaffold:{scaffold}",
                "effect": "bioactivity", "mechanism": "scaffold-dependent SAR",
                "confidence": conf, "evidence_count": count,
            }
            conn.execute(
                "INSERT OR IGNORE INTO causal_claims (id, cause, effect, mechanism, evidence_json, confidence, status, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, claim["cause"], claim["effect"], claim["mechanism"],
                 json.dumps([{"scaffold": scaffold, "active_compounds": count}]),
                 conf, "candidate", investigation_id, ts),
            )
            claims.append(claim)

        conn.commit()
        conn.close()
        logger.info(f"Inferred {len(claims)} causal claims")
        return claims

    def list_claims(self, status: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT id, cause, effect, mechanism, confidence, status FROM causal_claims WHERE status=?", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, cause, effect, mechanism, confidence, status FROM causal_claims").fetchall()
        conn.close()
        return [{"id": r[0], "cause": r[1], "effect": r[2], "mechanism": r[3], "confidence": r[4], "status": r[5]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM causal_claims").fetchone()[0]
        by_status = conn.execute("SELECT status, COUNT(*) FROM causal_claims GROUP BY status").fetchall()
        conn.close()
        return {"total": total, "by_status": {s: c for s, c in by_status}}


causal_inference = CausalInference()
