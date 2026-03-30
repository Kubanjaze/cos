"""COS relationship extractor — typed edges between entities.

Builds relations like "benz_001_F has_activity 7.25" from co-occurring entities.

Usage:
    from cos.memory.relations import relation_extractor
    n = relation_extractor.extract_from_document("doc-abc123")
    rels = relation_extractor.get_relations(entity_name="benz_001_F")
"""

import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.relations")

SCAFFOLD_FAMILIES = {"benz", "naph", "ind", "quin", "pyr", "bzim"}


@dataclass
class Relation:
    id: str
    source_entity: str
    relation_type: str
    target_value: str
    confidence: float
    source_chunk_id: str
    document_id: str
    created_at: str


class RelationExtractor:
    """Extracts typed relations between entities."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relations (
                    id TEXT PRIMARY KEY,
                    source_entity TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    target_value TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source_chunk_id TEXT,
                    document_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_entity, relation_type, target_value, document_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON entity_relations(source_entity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON entity_relations(relation_type)")

    def extract_from_document(self, doc_id: str) -> int:
        """Extract relations from document entities + text. Returns count."""
        from cos.memory.documents import document_store

        doc = document_store.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        chunks = document_store.get_chunks(doc.id)
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        for chunk in chunks:
            text = chunk.chunk_text

            # Extract compound → pIC50 co-occurrences from same line
            compound_pattern = re.compile(r'((?:benz|naph|ind|quin|pyr|bzim)_\d{3}_\w+)')
            pic50_pattern = re.compile(r'(\d+\.?\d*)\s*\|?\s*$', re.MULTILINE)

            # Parse lines looking for compound | smiles | pic50 pattern
            for line in text.split("\n"):
                line = line.strip()
                if not line or line.startswith("|:") or line.startswith("| compound"):
                    continue

                comp_match = compound_pattern.search(line)
                if comp_match:
                    compound = comp_match.group(1)

                    # Extract pIC50 from the line (last number)
                    numbers = re.findall(r'(\d+\.?\d+)', line)
                    if numbers:
                        pic50 = numbers[-1]  # last number is typically pIC50
                        try:
                            val = float(pic50)
                            if 4.0 <= val <= 10.0:  # reasonable pIC50 range
                                created += self._insert_relation(
                                    conn, compound, "has_activity", f"pIC50={pic50}",
                                    1.0, chunk.id, doc.id, ts
                                )
                        except ValueError:
                            pass

                    # Scaffold membership from name prefix
                    prefix = compound.split("_")[0]
                    if prefix in SCAFFOLD_FAMILIES:
                        created += self._insert_relation(
                            conn, compound, "belongs_to_scaffold", prefix,
                            1.0, chunk.id, doc.id, ts
                        )

        conn.commit()
        conn.close()

        logger.info(f"Extracted {created} relations from {doc.id}",
                     extra={"investigation_id": doc.investigation_id})
        return created

    def _insert_relation(self, conn, source, rel_type, target, confidence, chunk_id, doc_id, ts) -> int:
        rel_id = f"rel-{uuid.uuid4().hex[:8]}"
        try:
            conn.execute(
                "INSERT OR IGNORE INTO entity_relations (id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (rel_id, source, rel_type, target, confidence, chunk_id, doc_id, ts),
            )
            return 1 if conn.execute("SELECT changes()").fetchone()[0] > 0 else 0
        except Exception:
            return 0

    def get_relations(
        self,
        entity_name: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> list[Relation]:
        """Query relations with optional filters."""
        conn = self._get_conn()
        conditions = []
        params = []
        if entity_name:
            conditions.append("source_entity=?")
            params.append(entity_name)
        if relation_type:
            conditions.append("relation_type=?")
            params.append(relation_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at "
            f"FROM entity_relations WHERE {where} ORDER BY source_entity, relation_type",
            params,
        ).fetchall()
        conn.close()
        return [Relation(*r) for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        by_type = conn.execute(
            "SELECT relation_type, COUNT(*) FROM entity_relations GROUP BY relation_type"
        ).fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


# Singleton
relation_extractor = RelationExtractor()
