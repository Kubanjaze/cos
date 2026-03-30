"""COS pattern detection — find trends and clusters in knowledge.

Phase 148: Detects recurring patterns across entities, relations, and concepts.
"""

import sqlite3
from collections import Counter
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.patterns")


class PatternDetector:
    """Detects patterns, trends, and clusters in COS memory."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def detect_all(self) -> dict:
        """Run all pattern detectors."""
        return {
            "scaffold_patterns": self.scaffold_activity_patterns(),
            "relation_frequency": self.relation_frequency(),
            "entity_clusters": self.entity_type_clusters(),
            "domain_coverage": self.domain_coverage(),
        }

    def scaffold_activity_patterns(self) -> list[dict]:
        """Detect activity patterns per scaffold family."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT r1.target_value as scaffold, r2.source_entity, r2.target_value as activity
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
            ORDER BY r1.target_value
        """).fetchall()
        conn.close()

        scaffolds: dict[str, list[float]] = {}
        for scaffold, compound, activity in rows:
            if "pIC50=" in activity:
                try:
                    val = float(activity.replace("pIC50=", ""))
                    scaffolds.setdefault(scaffold, []).append(val)
                except ValueError:
                    pass

        patterns = []
        for scaffold, values in scaffolds.items():
            if values:
                avg = sum(values) / len(values)
                spread = max(values) - min(values) if len(values) > 1 else 0
                patterns.append({
                    "scaffold": scaffold, "compounds": len(values),
                    "avg_pIC50": round(avg, 2), "spread": round(spread, 2),
                    "trend": "tight" if spread < 1.0 else "variable",
                })
        return patterns

    def relation_frequency(self) -> list[dict]:
        """Most common relation types."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT relation_type, COUNT(*) FROM entity_relations GROUP BY relation_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return [{"relation": r[0], "count": r[1]} for r in rows]

    def entity_type_clusters(self) -> list[dict]:
        """Entity distribution by type."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return [{"type": r[0], "count": r[1]} for r in rows]

    def domain_coverage(self) -> list[dict]:
        """Concept coverage by domain."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT domain, COUNT(*), AVG(confidence) FROM concepts GROUP BY domain"
        ).fetchall()
        conn.close()
        return [{"domain": r[0], "concepts": r[1], "avg_confidence": round(r[2], 3)} for r in rows]

    def stats(self) -> dict:
        p = self.detect_all()
        return {
            "scaffold_patterns": len(p["scaffold_patterns"]),
            "relation_types": len(p["relation_frequency"]),
            "entity_types": len(p["entity_clusters"]),
            "domains": len(p["domain_coverage"]),
        }


pattern_detector = PatternDetector()
