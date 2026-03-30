"""COS explainability layer — make reasoning transparent and trustworthy. Phase 158."""

import sqlite3
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.explainability")


class ExplainabilityLayer:
    """Generates explanations for COS reasoning outputs."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def explain_hypothesis(self, hypothesis_id: str) -> dict:
        """Explain why a hypothesis was generated and its confidence."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, statement, evidence_json, confidence, status FROM hypotheses WHERE id=?",
            (hypothesis_id,),
        ).fetchone()
        conn.close()
        if not row:
            return {"error": "Hypothesis not found"}

        evidence = json.loads(row[2])
        return {
            "hypothesis_id": row[0], "statement": row[1], "confidence": row[3], "status": row[4],
            "explanation": {
                "basis": f"Generated from {len(evidence)} evidence item(s)",
                "confidence_factors": [
                    "Scaffold compound count contributes to confidence",
                    "Activity data consistency raises confidence",
                    "Disconfirmation challenges may lower confidence",
                ],
                "evidence_summary": evidence,
                "limitations": ["Rule-based pattern matching, not statistical inference",
                               "Limited to scaffold-activity relationships"],
            },
        }

    def explain_score(self, target_type: str, target_id: str) -> dict:
        """Explain why an item has a particular score."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT relevance, confidence, recency, frequency, composite_score "
            "FROM memory_scores WHERE target_type=? AND target_id=?",
            (target_type, target_id),
        ).fetchone()
        conn.close()
        if not row:
            return {"error": "Score not found"}

        rel, conf, rec, freq, composite = row
        return {
            "target": f"{target_type}/{target_id}",
            "composite_score": composite,
            "breakdown": {
                "relevance": {"value": rel, "weight": 0.3, "contribution": round(rel * 0.3, 4)},
                "confidence": {"value": conf, "weight": 0.3, "contribution": round(conf * 0.3, 4)},
                "recency": {"value": rec, "weight": 0.2, "contribution": round(rec * 0.2, 4)},
                "frequency": {"value": freq, "weight": 0.2, "note": "log-scaled, capped at ~148 accesses"},
            },
        }

    def explain_conflict(self, conflict_id: str) -> dict:
        """Explain a detected conflict."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, conflict_type, description, severity, status, resolution FROM conflicts WHERE id=? OR id LIKE ?",
            (conflict_id, conflict_id + "%"),
        ).fetchone()
        conn.close()
        if not row:
            return {"error": "Conflict not found"}

        return {
            "conflict_id": row[0], "type": row[1], "description": row[2],
            "severity": row[3], "status": row[4], "resolution": row[5] or "Unresolved",
            "explanation": f"Detected as '{row[1]}' with severity '{row[3]}'. "
                          f"{'Resolved: ' + row[5] if row[5] else 'Awaiting resolution.'}",
        }

    def stats(self) -> dict:
        conn = self._get_conn()
        try:
            hypotheses = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
        except Exception:
            hypotheses = 0
        scores = conn.execute("SELECT COUNT(*) FROM memory_scores").fetchone()[0]
        conflicts = conn.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0]
        conn.close()
        return {"explainable_hypotheses": hypotheses, "explainable_scores": scores, "explainable_conflicts": conflicts}


explainability_layer = ExplainabilityLayer()
