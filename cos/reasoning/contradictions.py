"""COS contradiction analyzer — deep analysis of conflicting knowledge.

Phase 143: Goes beyond Phase 131 conflict detection by analyzing WHY
contradictions exist and suggesting resolutions.
"""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.contradictions")


class ContradictionAnalyzer:
    """Analyzes contradictions and suggests resolutions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def analyze(self) -> list[dict]:
        """Analyze all open conflicts and produce resolution suggestions."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, conflict_type, item_a_type, item_a_id, item_b_type, item_b_id, description, severity "
            "FROM conflicts WHERE status='open' ORDER BY severity DESC"
        ).fetchall()
        conn.close()

        analyses = []
        for cid, ctype, a_type, a_id, b_type, b_id, desc, sev in rows:
            analysis = {
                "conflict_id": cid, "type": ctype, "severity": sev, "description": desc,
                "suggestion": self._suggest_resolution(ctype, sev),
                "impact": "high" if sev == "high" else "low",
            }
            analyses.append(analysis)

        logger.info(f"Analyzed {len(analyses)} contradictions")
        return analyses

    def _suggest_resolution(self, conflict_type: str, severity: str) -> str:
        suggestions = {
            "duplicate_concept": "Merge definitions or mark one as domain-specific alias",
            "contradictory_relation": "Verify source data; keep higher-confidence value",
            "confidence_disagreement": "Re-evaluate low-confidence source; consider deprecating",
        }
        return suggestions.get(conflict_type, "Manual review recommended")

    def stats(self) -> dict:
        conn = self._get_conn()
        open_count = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='resolved'").fetchone()[0]
        conn.close()
        return {"open": open_count, "resolved": resolved, "total": open_count + resolved}


contradiction_analyzer = ContradictionAnalyzer()
