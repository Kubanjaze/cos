"""COS tradeoff analysis + decision confidence scoring. Phase 185, 187."""

import sqlite3
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.tradeoffs")


class TradeoffAnalyzer:
    """Analyzes tradeoffs between decision options and scores confidence."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def analyze(self, decision_id: str) -> dict:
        """Analyze tradeoffs for a decision."""
        from cos.decision.schema import decision_store
        dec = decision_store.get(decision_id)
        if not dec:
            return {"error": "Decision not found"}

        actions = dec.actions
        risks = dec.risks

        pros = [a.get("description", "") for a in actions if a.get("impact") in ("high", "medium")]
        cons = [r.get("description", "") for r in risks if r.get("impact") in ("high", "medium")]

        # Phase 187: Decision confidence scoring
        base_conf = dec.confidence
        risk_penalty = len(risks) * 0.05
        action_bonus = min(0.1, len(actions) * 0.02)
        adjusted = round(max(0.1, min(0.99, base_conf - risk_penalty + action_bonus)), 3)

        return {
            "decision_id": decision_id, "title": dec.title,
            "pros": pros if pros else ["Addresses identified need"],
            "cons": cons if cons else ["No major risks identified"],
            "original_confidence": base_conf,
            "adjusted_confidence": adjusted,
            "risk_count": len(risks), "action_count": len(actions),
            "recommendation": "Proceed" if adjusted >= 0.6 else "Needs more evidence",
        }

    def compare_decisions(self, id_a: str, id_b: str) -> dict:
        """Compare two decisions. Phase 191 partial."""
        a = self.analyze(id_a)
        b = self.analyze(id_b)
        if "error" in a or "error" in b:
            return {"error": "One or both decisions not found"}

        winner = id_a if a["adjusted_confidence"] >= b["adjusted_confidence"] else id_b
        return {
            "a": {"id": id_a, "title": a["title"], "confidence": a["adjusted_confidence"]},
            "b": {"id": id_b, "title": b["title"], "confidence": b["adjusted_confidence"]},
            "winner": winner,
            "margin": round(abs(a["adjusted_confidence"] - b["adjusted_confidence"]), 3),
        }

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM decisions").fetchone()[0]
        conn.close()
        return {"total_decisions": total, "avg_confidence": round(avg_conf, 3)}


tradeoff_analyzer = TradeoffAnalyzer()
