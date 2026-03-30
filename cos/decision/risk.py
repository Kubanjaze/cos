"""COS risk assessment + invalidation conditions. Phase 183-184."""

import sqlite3
import json
import time
import uuid
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.risk")


class RiskAssessor:
    """Assesses risks for decisions and generates invalidation conditions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_assessments (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    risk_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    likelihood REAL NOT NULL DEFAULT 0.5,
                    impact TEXT NOT NULL DEFAULT 'medium',
                    mitigation TEXT NOT NULL DEFAULT '',
                    invalidation_condition TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

    def assess(self, decision_id: str) -> list[dict]:
        """Assess risks for a decision."""
        from cos.decision.schema import decision_store
        dec = decision_store.get(decision_id)
        if not dec:
            return [{"error": f"Decision not found: {decision_id}"}]

        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        risks = []

        # Risk: low confidence
        if dec.confidence < 0.7:
            rid = f"rsk-{uuid.uuid4().hex[:8]}"
            risk = {
                "id": rid, "type": "low_confidence",
                "description": f"Decision confidence ({dec.confidence:.2f}) below 0.7 threshold",
                "likelihood": round(1.0 - dec.confidence, 2), "impact": "high",
                "mitigation": "Gather more evidence before acting",
                "invalidation": f"Confidence drops below {dec.confidence * 0.8:.2f}",
            }
            conn.execute(
                "INSERT INTO risk_assessments (id, decision_id, risk_type, description, likelihood, impact, mitigation, invalidation_condition, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rid, decision_id, risk["type"], risk["description"], risk["likelihood"],
                 risk["impact"], risk["mitigation"], risk["invalidation"], ts),
            )
            risks.append(risk)

        # Risk: unresolved conflicts
        conflict_count = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        if conflict_count > 0:
            rid = f"rsk-{uuid.uuid4().hex[:8]}"
            risk = {
                "id": rid, "type": "unresolved_conflicts",
                "description": f"{conflict_count} open conflicts may affect decision validity",
                "likelihood": 0.4, "impact": "medium",
                "mitigation": "Resolve conflicts before finalizing decision",
                "invalidation": "Conflict resolution changes underlying evidence",
            }
            conn.execute(
                "INSERT INTO risk_assessments (id, decision_id, risk_type, description, likelihood, impact, mitigation, invalidation_condition, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rid, decision_id, risk["type"], risk["description"], risk["likelihood"],
                 risk["impact"], risk["mitigation"], risk["invalidation"], ts),
            )
            risks.append(risk)

        # Risk: missing evidence (knowledge gaps)
        try:
            gaps = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
            if gaps > 0:
                rid = f"rsk-{uuid.uuid4().hex[:8]}"
                risk = {
                    "id": rid, "type": "missing_evidence",
                    "description": f"{gaps} low-confidence concept(s) in knowledge base",
                    "likelihood": 0.3, "impact": "low",
                    "mitigation": "Improve concept confidence through additional sources",
                    "invalidation": "Key concept confidence drops to zero",
                }
                conn.execute(
                    "INSERT INTO risk_assessments (id, decision_id, risk_type, description, likelihood, impact, mitigation, invalidation_condition, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (rid, decision_id, risk["type"], risk["description"], risk["likelihood"],
                     risk["impact"], risk["mitigation"], risk["invalidation"], ts),
                )
                risks.append(risk)
        except Exception:
            pass

        conn.commit()
        conn.close()
        logger.info(f"Assessed {len(risks)} risks for decision {decision_id}")
        return risks

    def get_risks(self, decision_id: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, risk_type, description, likelihood, impact, mitigation, invalidation_condition "
            "FROM risk_assessments WHERE decision_id=? ORDER BY likelihood DESC", (decision_id,)
        ).fetchall()
        conn.close()
        return [{"id": r[0], "type": r[1], "description": r[2], "likelihood": r[3],
                 "impact": r[4], "mitigation": r[5], "invalidation": r[6]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM risk_assessments").fetchone()[0]
        by_type = conn.execute("SELECT risk_type, COUNT(*) FROM risk_assessments GROUP BY risk_type").fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


risk_assessor = RiskAssessor()
