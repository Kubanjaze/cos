"""COS multi-source synthesis engine — combine inputs into unified insights.

Phase 141: Merges findings from multiple documents, entities, and concepts
into a coherent synthesis with source attribution.

Usage:
    from cos.reasoning.synthesis import synthesis_engine
    result = synthesis_engine.synthesize("CETP inhibitors", investigation_id="inv-001")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.synthesis")


@dataclass
class Synthesis:
    id: str
    query: str
    sources: list[dict]
    summary: str
    source_count: int
    investigation_id: str
    created_at: str


class SynthesisEngine:
    """Combines multiple knowledge sources into unified insights."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS syntheses (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_count INTEGER NOT NULL,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def synthesize(self, query: str, investigation_id: str = "default") -> Synthesis:
        """Gather and synthesize information from multiple sources."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        sources = []
        pattern = f"%{query}%"

        # Gather from concepts
        rows = conn.execute(
            "SELECT id, name, definition, domain, confidence FROM concepts "
            "WHERE name_lower LIKE ? OR definition LIKE ? ORDER BY confidence DESC LIMIT 10",
            (pattern.lower(), pattern),
        ).fetchall()
        for cid, name, defn, domain, conf in rows:
            sources.append({"type": "concept", "id": cid, "name": name,
                           "content": defn[:200], "domain": domain, "confidence": conf})

        # Gather from entities
        rows = conn.execute(
            "SELECT id, name, entity_type, confidence FROM entities WHERE name LIKE ? LIMIT 10",
            (pattern,),
        ).fetchall()
        for eid, name, etype, conf in rows:
            sources.append({"type": "entity", "id": eid, "name": name,
                           "content": f"{etype}: {name}", "confidence": conf})

        # Gather from document chunks
        rows = conn.execute(
            "SELECT c.id, d.title, c.chunk_text FROM document_chunks c "
            "JOIN documents d ON c.document_id = d.id WHERE c.chunk_text LIKE ? LIMIT 5",
            (pattern,),
        ).fetchall()
        for chk_id, title, text in rows:
            sources.append({"type": "chunk", "id": chk_id, "name": title,
                           "content": text[:200], "confidence": 0.7})

        # Build synthesis summary
        if sources:
            source_types = set(s["type"] for s in sources)
            avg_conf = sum(s.get("confidence", 0.5) for s in sources) / len(sources)
            summary = (f"Synthesis for '{query}': {len(sources)} sources across "
                      f"{', '.join(source_types)}. Average confidence: {avg_conf:.2f}.")
        else:
            summary = f"No sources found for '{query}'."

        import json
        sid = f"syn-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO syntheses (id, query, summary, source_count, sources_json, investigation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, query, summary, len(sources), json.dumps(sources), investigation_id, ts),
        )
        conn.commit()
        conn.close()

        logger.info(f"Synthesis complete: '{query}' ({len(sources)} sources)")
        return Synthesis(id=sid, query=query, sources=sources, summary=summary,
                        source_count=len(sources), investigation_id=investigation_id, created_at=ts)

    def list_syntheses(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, query, source_count, investigation_id, created_at FROM syntheses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [{"id": r[0], "query": r[1], "sources": r[2], "investigation": r[3], "created_at": r[4]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM syntheses").fetchone()[0]
        avg_sources = conn.execute("SELECT COALESCE(AVG(source_count), 0) FROM syntheses").fetchone()[0]
        conn.close()
        return {"total": total, "avg_sources": round(avg_sources, 1)}


synthesis_engine = SynthesisEngine()
