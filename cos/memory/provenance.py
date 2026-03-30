"""COS provenance tracking — source traceability for all outputs.

Every COS output (entity, relation, concept, episode) can be traced back
through the processing chain to its original source file.

Addresses Architect Notes risk #5: "If sources aren't traceable, outputs
won't be trusted."

Usage:
    from cos.memory.provenance import provenance_tracker
    provenance_tracker.register("entity", "ent-abc", "chunk", "chk-123",
                                operation="extract_entity", agent="cos.memory.entities")
    chain = provenance_tracker.trace("entity", "ent-abc")
    derived = provenance_tracker.chain("art-xyz")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.provenance")


@dataclass
class ProvenanceLink:
    id: str
    target_type: str
    target_id: str
    source_type: str
    source_id: str
    operation: str
    agent: str
    investigation_id: str
    created_at: str


class ProvenanceTracker:
    """Tracks provenance links between COS objects."""

    _COLS = (
        "id, target_type, target_id, source_type, source_id, "
        "operation, agent, investigation_id, created_at"
    )

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provenance (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    agent TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    UNIQUE(target_type, target_id, source_type, source_id, operation)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_target ON provenance(target_type, target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_source ON provenance(source_type, source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_op ON provenance(operation)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_inv ON provenance(investigation_id)")

    def register(
        self,
        target_type: str,
        target_id: str,
        source_type: str,
        source_id: str,
        operation: str,
        agent: str = "",
        investigation_id: str = "default",
    ) -> str:
        """Record a provenance link. Returns link ID."""
        link_id = f"prv-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO provenance "
                    "(id, target_type, target_id, source_type, source_id, operation, agent, investigation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (link_id, target_type, target_id, source_type, source_id,
                     operation, agent, investigation_id, ts),
                )
            except Exception as e:
                logger.warning(f"Provenance register error: {e}")
                return ""

        logger.info(f"Provenance: {target_type}/{target_id[:12]} ← {source_type}/{source_id[:12]} [{operation}]")
        return link_id

    def trace(self, target_type: str, target_id: str) -> list[ProvenanceLink]:
        """Trace backward: find all sources for a given output."""
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT {self._COLS} FROM provenance "
            f"WHERE target_type=? AND target_id=? ORDER BY created_at",
            (target_type, target_id),
        ).fetchall()
        conn.close()
        return [ProvenanceLink(*r) for r in rows]

    def chain(self, source_type: str, source_id: str) -> list[ProvenanceLink]:
        """Trace forward: find all outputs derived from a given source."""
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT {self._COLS} FROM provenance "
            f"WHERE source_type=? AND source_id=? ORDER BY created_at",
            (source_type, source_id),
        ).fetchall()
        conn.close()
        return [ProvenanceLink(*r) for r in rows]

    def get_lineage(self, target_type: str, target_id: str, max_depth: int = 10) -> list[dict]:
        """Walk full lineage tree to root. Returns list of steps from target to source."""
        lineage: list[dict] = []
        visited: set[tuple[str, str]] = set()

        current_type = target_type
        current_id = target_id

        for _ in range(max_depth):
            key = (current_type, current_id)
            if key in visited:
                break
            visited.add(key)

            links = self.trace(current_type, current_id)
            if not links:
                break

            link = links[0]  # Follow first (primary) source
            lineage.append({
                "target_type": link.target_type,
                "target_id": link.target_id,
                "source_type": link.source_type,
                "source_id": link.source_id,
                "operation": link.operation,
                "agent": link.agent,
            })
            current_type = link.source_type
            current_id = link.source_id

        return lineage

    def backfill(self) -> int:
        """Reconstruct provenance from existing FK links in the database."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        # documents → artifacts
        rows = conn.execute(
            "SELECT id, artifact_id, investigation_id FROM documents"
        ).fetchall()
        for doc_id, art_id, inv_id in rows:
            created += self._insert_link(
                conn, "document", doc_id, "artifact", art_id,
                "ingest", "cos.memory.documents", inv_id, ts
            )

        # chunks → documents
        rows = conn.execute(
            "SELECT c.id, c.document_id, d.investigation_id "
            "FROM document_chunks c JOIN documents d ON c.document_id = d.id"
        ).fetchall()
        for chunk_id, doc_id, inv_id in rows:
            created += self._insert_link(
                conn, "chunk", chunk_id, "document", doc_id,
                "chunk", "cos.memory.documents", inv_id, ts
            )

        # entities → chunks
        rows = conn.execute(
            "SELECT id, source_chunk_id, document_id, investigation_id FROM entities WHERE source_chunk_id IS NOT NULL"
        ).fetchall()
        for ent_id, chunk_id, doc_id, inv_id in rows:
            created += self._insert_link(
                conn, "entity", ent_id, "chunk", chunk_id,
                "extract_entity", "cos.memory.entities", inv_id, ts
            )

        # relations → chunks
        rows = conn.execute(
            "SELECT id, source_chunk_id, document_id FROM entity_relations WHERE source_chunk_id IS NOT NULL"
        ).fetchall()
        for rel_id, chunk_id, doc_id in rows:
            created += self._insert_link(
                conn, "relation", rel_id, "chunk", chunk_id,
                "extract_relation", "cos.memory.relations", "default", ts
            )

        # embeddings → chunks
        try:
            rows = conn.execute(
                "SELECT id, chunk_id FROM chunk_embeddings"
            ).fetchall()
            for emb_id, chunk_id in rows:
                created += self._insert_link(
                    conn, "embedding", emb_id, "chunk", chunk_id,
                    "embed", "cos.memory.embeddings", "default", ts
                )
        except Exception:
            pass  # Table may not exist yet

        conn.commit()
        conn.close()

        logger.info(f"Provenance backfill: {created} links created")
        return created

    def _insert_link(self, conn, target_type, target_id, source_type, source_id,
                     operation, agent, investigation_id, ts) -> int:
        link_id = f"prv-{uuid.uuid4().hex[:8]}"
        try:
            conn.execute(
                "INSERT OR IGNORE INTO provenance "
                "(id, target_type, target_id, source_type, source_id, operation, agent, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (link_id, target_type, target_id, source_type, source_id,
                 operation, agent, investigation_id, ts),
            )
            return 1 if conn.execute("SELECT changes()").fetchone()[0] > 0 else 0
        except Exception:
            return 0

    def stats(self) -> dict:
        """Provenance statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
        by_operation = conn.execute(
            "SELECT operation, COUNT(*) FROM provenance GROUP BY operation ORDER BY COUNT(*) DESC"
        ).fetchall()
        by_target = conn.execute(
            "SELECT target_type, COUNT(*) FROM provenance GROUP BY target_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "by_operation": {op: c for op, c in by_operation},
            "by_target_type": {t: c for t, c in by_target},
        }


# Singleton
provenance_tracker = ProvenanceTracker()
