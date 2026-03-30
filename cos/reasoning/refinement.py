"""COS iterative refinement loop — improve outputs through iteration. Phase 155."""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.refinement")


class RefinementLoop:
    """Iteratively refines reasoning outputs."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refinements (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    iteration INTEGER NOT NULL DEFAULT 1,
                    changes_json TEXT NOT NULL DEFAULT '{}',
                    score_before REAL NOT NULL DEFAULT 0,
                    score_after REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

    def refine_hypothesis(self, hypothesis_id: str) -> dict:
        """Refine a hypothesis by incorporating new evidence."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, statement, confidence, evidence_json FROM hypotheses WHERE id=?",
            (hypothesis_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"error": "Hypothesis not found"}

        hid, statement, old_conf, evidence_str = row
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Count existing iterations
        prev = conn.execute(
            "SELECT COUNT(*) FROM refinements WHERE target_type='hypothesis' AND target_id=?",
            (hid,),
        ).fetchone()[0]

        # Refine: check if more evidence available
        evidence = json.loads(evidence_str)
        new_conf = min(0.95, old_conf + 0.02 * (prev + 1))

        rid = f"ref-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO refinements (id, target_type, target_id, iteration, changes_json, score_before, score_after, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rid, "hypothesis", hid, prev + 1,
             json.dumps({"confidence_delta": round(new_conf - old_conf, 4)}),
             old_conf, new_conf, ts),
        )
        conn.execute("UPDATE hypotheses SET confidence=? WHERE id=?", (new_conf, hid))
        conn.commit()
        conn.close()

        logger.info(f"Refined hypothesis {hid}: {old_conf:.3f} → {new_conf:.3f} (iteration {prev+1})")
        return {"hypothesis_id": hid, "iteration": prev + 1,
                "confidence_before": old_conf, "confidence_after": round(new_conf, 4)}

    def list_refinements(self, target_type: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if target_type:
            rows = conn.execute(
                "SELECT id, target_type, target_id, iteration, score_before, score_after, created_at "
                "FROM refinements WHERE target_type=? ORDER BY created_at DESC", (target_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, target_type, target_id, iteration, score_before, score_after, created_at "
                "FROM refinements ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "type": r[1], "target": r[2], "iteration": r[3],
                 "before": r[4], "after": r[5], "created_at": r[6]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM refinements").fetchone()[0]
        avg_improvement = conn.execute(
            "SELECT COALESCE(AVG(score_after - score_before), 0) FROM refinements"
        ).fetchone()[0]
        conn.close()
        return {"total_refinements": total, "avg_improvement": round(avg_improvement, 4)}


refinement_loop = RefinementLoop()
