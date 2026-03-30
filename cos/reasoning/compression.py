"""COS summary compression — reduce complexity while preserving key info. Phase 152."""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.compression")


class CompressionEngine:
    """Compresses knowledge into concise summaries."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def compress_investigation(self, investigation_id: str = "default") -> dict:
        """Generate compressed summary of an investigation."""
        conn = self._get_conn()
        artifacts = conn.execute("SELECT COUNT(*) FROM artifacts WHERE investigation_id=?", (investigation_id,)).fetchone()[0]
        entities = conn.execute("SELECT COUNT(*) FROM entities WHERE investigation_id=?", (investigation_id,)).fetchone()[0]
        concepts = conn.execute("SELECT COUNT(*) FROM concepts WHERE investigation_id=?", (investigation_id,)).fetchone()[0]
        episodes = conn.execute("SELECT COUNT(*) FROM episodes WHERE investigation_id=?", (investigation_id,)).fetchone()[0]

        top_concepts = conn.execute(
            "SELECT name, confidence FROM concepts WHERE investigation_id=? ORDER BY confidence DESC LIMIT 5",
            (investigation_id,),
        ).fetchall()

        top_entities = conn.execute(
            "SELECT entity_type, COUNT(*) FROM entities WHERE investigation_id=? GROUP BY entity_type ORDER BY COUNT(*) DESC",
            (investigation_id,),
        ).fetchall()

        conn.close()

        summary_parts = [f"Investigation '{investigation_id}': {artifacts} artifacts, {entities} entities, {concepts} concepts, {episodes} episodes."]
        if top_concepts:
            concept_str = ", ".join(f"{n} ({c:.0%})" for n, c in top_concepts)
            summary_parts.append(f"Key concepts: {concept_str}.")
        if top_entities:
            ent_str = ", ".join(f"{c} {t}" for t, c in top_entities)
            summary_parts.append(f"Entity types: {ent_str}.")

        return {
            "investigation_id": investigation_id,
            "summary": " ".join(summary_parts),
            "stats": {"artifacts": artifacts, "entities": entities, "concepts": concepts, "episodes": episodes},
            "compression_ratio": round(len(" ".join(summary_parts)) / max(1, (artifacts + entities + concepts) * 50), 2),
        }

    def compress_domain(self, domain: str) -> dict:
        """Compress all knowledge in a domain."""
        conn = self._get_conn()
        concepts = conn.execute(
            "SELECT name, definition, confidence FROM concepts WHERE domain=? ORDER BY confidence DESC",
            (domain,),
        ).fetchall()
        conn.close()

        if not concepts:
            return {"domain": domain, "summary": f"No knowledge in domain '{domain}'.", "concept_count": 0}

        top = concepts[:5]
        summary = f"Domain '{domain}': {len(concepts)} concepts. Top: " + "; ".join(
            f"{n} ({c:.0%})" for n, d, c in top
        )
        return {"domain": domain, "summary": summary, "concept_count": len(concepts)}

    def stats(self) -> dict:
        conn = self._get_conn()
        total_concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        domains = conn.execute("SELECT COUNT(DISTINCT domain) FROM concepts").fetchone()[0]
        conn.close()
        return {"total_concepts": total_concepts, "domains": domains}


compression_engine = CompressionEngine()
