"""COS decision tracking + feedback loop. Phase 189-190.

Also covers: Phase 191 (multi-option scenario board), Phase 192 (time-sensitive),
Phase 193 (resource allocation), Phase 194 (audit trail).
"""

import sqlite3
import json
import time
import uuid
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.tracking")


class DecisionTracker:
    """Tracks decision outcomes and provides feedback into reasoning."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_outcomes (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    outcome_type TEXT NOT NULL DEFAULT 'unknown',
                    predicted_confidence REAL NOT NULL DEFAULT 0,
                    actual_result TEXT NOT NULL DEFAULT '',
                    feedback TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_do_dec ON decision_outcomes(decision_id)")

            # Phase 194: Audit trail
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_audit (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    actor TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_da_dec ON decision_audit(decision_id)")

    def record_outcome(self, decision_id: str, outcome: str,
                       outcome_type: str = "unknown", actual_result: str = "") -> str:
        """Record the outcome of a decision. Phase 189."""
        from cos.decision.schema import decision_store
        dec = decision_store.get(decision_id)
        if not dec:
            raise ValueError(f"Decision not found: {decision_id}")

        oid = f"out-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO decision_outcomes (id, decision_id, outcome, outcome_type, predicted_confidence, actual_result, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (oid, decision_id, outcome, outcome_type, dec.confidence, actual_result, ts),
            )
            # Audit trail
            conn.execute(
                "INSERT INTO decision_audit (id, decision_id, action, details, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"aud-{uuid.uuid4().hex[:8]}", decision_id, "outcome_recorded",
                 f"{outcome_type}: {outcome[:100]}", ts),
            )

        # Phase 190: Feedback loop — update decision status
        decision_store.update_status(decision_id, f"outcome:{outcome_type}")
        logger.info(f"Outcome recorded for {decision_id}: {outcome_type}")
        return oid

    def get_outcomes(self, decision_id: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, outcome, outcome_type, predicted_confidence, actual_result, created_at "
            "FROM decision_outcomes WHERE decision_id=? ORDER BY created_at", (decision_id,)
        ).fetchall()
        conn.close()
        return [{"id": r[0], "outcome": r[1], "type": r[2], "predicted_conf": r[3],
                 "actual": r[4], "created_at": r[5]} for r in rows]

    def calibration_report(self) -> dict:
        """How well do predicted confidences match actual outcomes? Phase 190."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT predicted_confidence, outcome_type FROM decision_outcomes"
        ).fetchall()
        conn.close()

        if not rows:
            return {"total_outcomes": 0, "calibration": "no data"}

        correct = sum(1 for conf, otype in rows if otype == "correct")
        total = len(rows)
        avg_conf = sum(r[0] for r in rows) / total
        accuracy = correct / total if total > 0 else 0

        return {
            "total_outcomes": total, "correct": correct, "accuracy": round(accuracy, 3),
            "avg_predicted_confidence": round(avg_conf, 3),
            "calibration_gap": round(abs(avg_conf - accuracy), 3),
        }

    def get_audit_trail(self, decision_id: str) -> list[dict]:
        """Phase 194: Full audit trail for a decision."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, action, details, actor, created_at FROM decision_audit "
            "WHERE decision_id=? ORDER BY created_at", (decision_id,)
        ).fetchall()
        conn.close()
        return [{"id": r[0], "action": r[1], "details": r[2], "actor": r[3], "created_at": r[4]} for r in rows]

    def scenario_board(self) -> list[dict]:
        """Phase 191: Compare all proposed decisions side by side."""
        from cos.decision.schema import decision_store
        decisions = decision_store.list_decisions(status="proposed")
        board = []
        for d in decisions:
            board.append({
                "id": d.id, "title": d.title, "confidence": d.confidence,
                "actions": len(d.actions), "risks": len(d.risks),
                "invalidations": len(d.invalidation_conditions),
            })
        board.sort(key=lambda x: x["confidence"], reverse=True)
        return board

    def urgency_score(self, decision_id: str, deadline_days: int = 30) -> dict:
        """Phase 192: Time-sensitive decision scoring."""
        from cos.decision.schema import decision_store
        dec = decision_store.get(decision_id)
        if not dec:
            return {"error": "Decision not found"}

        import math
        urgency = round(1.0 / (1 + math.exp(-0.1 * (15 - deadline_days))), 3)  # sigmoid centered at 15 days
        adjusted = round(dec.confidence * (1 + 0.2 * urgency), 3)

        return {
            "decision_id": decision_id, "deadline_days": deadline_days,
            "urgency_score": urgency, "base_confidence": dec.confidence,
            "time_adjusted_confidence": min(0.99, adjusted),
            "recommendation": "Act now" if urgency > 0.7 else "Can wait",
        }

    def allocate_resources(self) -> list[dict]:
        """Phase 193: Suggest resource allocation across decisions."""
        from cos.decision.schema import decision_store
        decisions = decision_store.list_decisions(status="proposed")
        total_weight = sum(d.confidence for d in decisions) or 1

        allocations = []
        for d in decisions:
            share = round(d.confidence / total_weight, 3)
            allocations.append({
                "decision_id": d.id, "title": d.title,
                "confidence": d.confidence, "resource_share": share,
                "suggested_effort": f"{share * 100:.0f}% of resources",
            })
        allocations.sort(key=lambda x: x["resource_share"], reverse=True)
        return allocations

    def stats(self) -> dict:
        conn = self._get_conn()
        outcomes = conn.execute("SELECT COUNT(*) FROM decision_outcomes").fetchone()[0]
        audits = conn.execute("SELECT COUNT(*) FROM decision_audit").fetchone()[0]
        conn.close()
        return {"total_outcomes": outcomes, "total_audit_entries": audits}


decision_tracker = DecisionTracker()
