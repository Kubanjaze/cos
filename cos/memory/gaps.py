"""COS knowledge gap detection — identify what we don't know.

Analyzes memory coverage to find missing relationships, undefined concepts,
and areas with low confidence.

Usage:
    from cos.memory.gaps import gap_detector
    gaps = gap_detector.detect_all()
"""

import sqlite3
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.gaps")


class GapDetector:
    """Detects knowledge gaps in COS memory."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def detect_all(self) -> dict:
        """Run all gap detectors. Returns summary."""
        return {
            "unlinked_entities": self.find_unlinked_entities(),
            "low_confidence_concepts": self.find_low_confidence(),
            "orphan_chunks": self.find_orphan_chunks(),
            "missing_provenance": self.find_missing_provenance(),
            "sparse_domains": self.find_sparse_domains(),
        }

    def find_unlinked_entities(self) -> list[dict]:
        """Find entities with no relations."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT e.id, e.name, e.entity_type, e.document_id
            FROM entities e
            LEFT JOIN entity_relations r ON e.name = r.source_entity
            WHERE r.id IS NULL
        """).fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "type": r[2], "doc": r[3]} for r in rows]

    def find_low_confidence(self, threshold: float = 0.5) -> list[dict]:
        """Find concepts with low confidence."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, domain, confidence FROM concepts WHERE confidence < ? ORDER BY confidence",
            (threshold,),
        ).fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "domain": r[2], "confidence": r[3]} for r in rows]

    def find_orphan_chunks(self) -> list[dict]:
        """Find chunks with no entities extracted."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT c.id, c.document_id, c.chunk_index, c.char_count
            FROM document_chunks c
            LEFT JOIN entities e ON c.id = e.source_chunk_id
            WHERE e.id IS NULL
        """).fetchall()
        conn.close()
        return [{"chunk_id": r[0], "doc_id": r[1], "index": r[2], "chars": r[3]} for r in rows]

    def find_missing_provenance(self) -> list[dict]:
        """Find entities/relations with no provenance record."""
        conn = self._get_conn()
        gaps = []

        # Entities without provenance
        rows = conn.execute("""
            SELECT e.id, e.name, e.entity_type
            FROM entities e
            LEFT JOIN provenance p ON p.target_type='entity' AND p.target_id=e.id
            WHERE p.id IS NULL
        """).fetchall()
        for r in rows:
            gaps.append({"type": "entity", "id": r[0], "name": r[1], "detail": r[2]})

        conn.close()
        return gaps

    def find_sparse_domains(self) -> list[dict]:
        """Find domains with fewer than 3 concepts."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM concepts GROUP BY domain HAVING cnt < 3 ORDER BY cnt"
        ).fetchall()
        conn.close()
        return [{"domain": r[0], "concept_count": r[1]} for r in rows]

    def summary(self) -> dict:
        """Quick summary of all gaps."""
        gaps = self.detect_all()
        return {
            "unlinked_entities": len(gaps["unlinked_entities"]),
            "low_confidence_concepts": len(gaps["low_confidence_concepts"]),
            "orphan_chunks": len(gaps["orphan_chunks"]),
            "missing_provenance": len(gaps["missing_provenance"]),
            "sparse_domains": len(gaps["sparse_domains"]),
            "total_gaps": sum(len(v) for v in gaps.values()),
        }


# Singleton
gap_detector = GapDetector()
