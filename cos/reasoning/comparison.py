"""COS comparison engine — structured A vs B analysis. Phase 151."""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.comparison")


class ComparisonEngine:
    """Compares two items across multiple dimensions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def compare_scaffolds(self, scaffold_a: str, scaffold_b: str) -> dict:
        """Compare two scaffold families."""
        conn = self._get_conn()
        result = {"a": self._scaffold_profile(conn, scaffold_a),
                  "b": self._scaffold_profile(conn, scaffold_b)}
        conn.close()

        # Determine winner
        a_score = result["a"]["avg_pIC50"] if result["a"]["avg_pIC50"] else 0
        b_score = result["b"]["avg_pIC50"] if result["b"]["avg_pIC50"] else 0
        result["winner"] = scaffold_a if a_score >= b_score else scaffold_b
        result["margin"] = round(abs(a_score - b_score), 2)
        return result

    def _scaffold_profile(self, conn, scaffold: str) -> dict:
        rows = conn.execute("""
            SELECT r2.source_entity, r2.target_value
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r1.target_value=?
            AND r2.relation_type='has_activity'
        """, (scaffold,)).fetchall()

        values = []
        for comp, act in rows:
            if "pIC50=" in act:
                try:
                    values.append(float(act.replace("pIC50=", "")))
                except ValueError:
                    pass

        count = conn.execute(
            "SELECT COUNT(*) FROM entity_relations WHERE relation_type='belongs_to_scaffold' AND target_value=?",
            (scaffold,),
        ).fetchone()[0]

        return {
            "scaffold": scaffold, "compounds": count,
            "active_compounds": len(values),
            "avg_pIC50": round(sum(values) / len(values), 2) if values else None,
            "max_pIC50": round(max(values), 2) if values else None,
            "min_pIC50": round(min(values), 2) if values else None,
        }

    def compare_concepts(self, name_a: str, name_b: str) -> dict:
        """Compare two concepts."""
        conn = self._get_conn()
        a = conn.execute("SELECT name, definition, domain, confidence FROM concepts WHERE name_lower=?",
                         (name_a.lower(),)).fetchone()
        b = conn.execute("SELECT name, definition, domain, confidence FROM concepts WHERE name_lower=?",
                         (name_b.lower(),)).fetchone()
        conn.close()

        return {
            "a": {"name": a[0], "definition": a[1][:100], "domain": a[2], "confidence": a[3]} if a else None,
            "b": {"name": b[0], "definition": b[1][:100], "domain": b[2], "confidence": b[3]} if b else None,
            "winner": (a[0] if a and (not b or a[3] >= b[3]) else b[0] if b else "none"),
        }

    def stats(self) -> dict:
        conn = self._get_conn()
        scaffolds = conn.execute("SELECT COUNT(DISTINCT target_value) FROM entity_relations WHERE relation_type='belongs_to_scaffold'").fetchone()[0]
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        conn.close()
        return {"comparable_scaffolds": scaffolds, "comparable_concepts": concepts}


comparison_engine = ComparisonEngine()
