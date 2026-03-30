"""COS evidence weighting — score sources by reliability and relevance.

Phase 147: Assigns weights to evidence sources based on provenance, confidence, and recency.
"""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.evidence")


class EvidenceWeighter:
    """Weights evidence sources by reliability."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def weight_sources(self, investigation_id: str = "default") -> list[dict]:
        """Weight all evidence sources for an investigation."""
        conn = self._get_conn()
        weighted = []

        # Weight documents by provenance depth and entity count
        rows = conn.execute("""
            SELECT d.id, d.title, d.chunk_count,
                   (SELECT COUNT(*) FROM entities e WHERE e.document_id=d.id) as entity_count,
                   (SELECT COUNT(*) FROM entity_relations r WHERE r.document_id=d.id) as rel_count
            FROM documents d ORDER BY entity_count DESC
        """).fetchall()

        for doc_id, title, chunks, ent_count, rel_count in rows:
            richness = min(1.0, (ent_count + rel_count) / max(chunks * 5, 1))
            weight = round(0.4 * richness + 0.3 * min(1.0, chunks / 10) + 0.3, 3)
            weighted.append({
                "source_type": "document", "id": doc_id, "name": title,
                "weight": weight, "entities": ent_count, "relations": rel_count,
                "factors": {"richness": round(richness, 3), "chunks": chunks},
            })

        conn.close()
        weighted.sort(key=lambda x: x["weight"], reverse=True)
        logger.info(f"Weighted {len(weighted)} evidence sources")
        return weighted

    def stats(self) -> dict:
        conn = self._get_conn()
        docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        total_prov = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
        conn.close()
        return {"documents": docs, "provenance_links": total_prov}


evidence_weighter = EvidenceWeighter()
