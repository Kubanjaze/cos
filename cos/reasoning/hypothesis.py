"""COS hypothesis generator — generate explanations from evidence.

Phase 144: Creates structured hypotheses from patterns in memory.
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.hypothesis")


class HypothesisGenerator:
    """Generates hypotheses from evidence patterns."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hypotheses (
                    id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    status TEXT NOT NULL DEFAULT 'proposed',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def generate(self, domain: str = "general", investigation_id: str = "default") -> list[dict]:
        """Generate hypotheses from entity/relation patterns."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        hypotheses = []

        # Pattern: scaffold families with high activity
        rows = conn.execute("""
            SELECT r.target_value as scaffold, COUNT(*) as cnt,
                   GROUP_CONCAT(DISTINCT r.source_entity) as compounds
            FROM entity_relations r WHERE r.relation_type='belongs_to_scaffold'
            GROUP BY r.target_value HAVING cnt >= 3 ORDER BY cnt DESC
        """).fetchall()

        for scaffold, count, compounds in rows:
            # Check if scaffold compounds have activity data
            activity_rows = conn.execute("""
                SELECT source_entity, target_value FROM entity_relations
                WHERE relation_type='has_activity' AND source_entity IN
                (SELECT source_entity FROM entity_relations WHERE relation_type='belongs_to_scaffold' AND target_value=?)
            """, (scaffold,)).fetchall()

            if activity_rows:
                vals = [float(a[1].replace("pIC50=", "")) for a in activity_rows if "pIC50=" in a[1]]
                if vals:
                    avg_act = sum(vals) / len(vals)
                    statement = (f"Scaffold '{scaffold}' ({count} compounds) shows consistent activity "
                               f"(avg pIC50={avg_act:.2f}), suggesting scaffold-dependent SAR")
                    evidence = [{"scaffold": scaffold, "compounds": count, "avg_pIC50": round(avg_act, 2)}]

                    hid = f"hyp-{uuid.uuid4().hex[:8]}"
                    conf = min(0.9, 0.5 + count * 0.05)
                    conn.execute(
                        "INSERT INTO hypotheses (id, statement, evidence_json, confidence, status, investigation_id, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (hid, statement, json.dumps(evidence), conf, "proposed", investigation_id, ts),
                    )
                    hypotheses.append({"id": hid, "statement": statement, "confidence": conf, "evidence": evidence})

        conn.commit()
        conn.close()
        logger.info(f"Generated {len(hypotheses)} hypotheses")
        return hypotheses

    def list_hypotheses(self, status: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT id, statement, confidence, status, created_at FROM hypotheses WHERE status=? ORDER BY confidence DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, statement, confidence, status, created_at FROM hypotheses ORDER BY confidence DESC"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "statement": r[1], "confidence": r[2], "status": r[3], "created_at": r[4]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
        by_status = conn.execute("SELECT status, COUNT(*) FROM hypotheses GROUP BY status").fetchall()
        avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM hypotheses").fetchone()[0]
        conn.close()
        return {"total": total, "avg_confidence": round(avg_conf, 3), "by_status": {s: c for s, c in by_status}}


hypothesis_generator = HypothesisGenerator()
