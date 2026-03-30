"""COS structured entity extraction.

Extracts typed entities (compounds, targets, activities) from document chunks.

Usage:
    from cos.memory.entities import entity_extractor
    n = entity_extractor.extract_from_document("doc-abc123")
    entities = entity_extractor.get_entities(entity_type="compound")
"""

import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.entities")


@dataclass
class Entity:
    id: str
    entity_type: str
    name: str
    value: str
    source_chunk_id: str
    document_id: str
    investigation_id: str
    confidence: float
    created_at: str


# ── Extraction patterns ─────────────────────────────────────────────────

PATTERNS = {
    "compound": [
        re.compile(r'\b((?:benz|naph|ind|quin|pyr|bzim)_\d{3}_\w+)\b'),
        re.compile(r'\b(CHEMBL\d{4,})\b'),
        re.compile(r'\b(sotorasib|adagrasib|divarasib|olomorasib|anacetrapib|torcetrapib)\b', re.I),
    ],
    "target": [
        re.compile(r'\b(KRAS|CETP|BRAF|SOS1|RAF1|EGFR|HER2|ALK)\b'),
        re.compile(r'\b(GTPase KRas)\b'),
    ],
    "activity_value": [
        re.compile(r'pIC50[=:\s]*(\d+\.?\d*)'),
        re.compile(r'IC50[=:\s]*(\d+\.?\d*)\s*(nM|uM|µM)'),
    ],
    "scaffold": [
        re.compile(r'\b(benz|naph|ind|quin|pyr|bzim)\b'),
    ],
}


def _extract_entities_from_text(text: str) -> list[dict]:
    """Extract entities from a text string using regex patterns."""
    found = []
    seen = set()

    for etype, patterns in PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                name = match.group(1) if match.lastindex else match.group(0)
                key = (etype, name.lower())
                if key not in seen:
                    seen.add(key)
                    found.append({
                        "entity_type": etype,
                        "name": name,
                        "value": name,
                        "confidence": 1.0,
                    })

    return found


class EntityExtractor:
    """Extracts and stores structured entities from document chunks."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source_chunk_id TEXT,
                    document_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    UNIQUE(entity_type, name, document_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ent_type ON entities(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ent_doc ON entities(document_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ent_inv ON entities(investigation_id)")

    def extract_from_document(self, doc_id: str) -> int:
        """Extract entities from all chunks of a document. Returns count."""
        from cos.memory.documents import document_store

        doc = document_store.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        chunks = document_store.get_chunks(doc.id)
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        for chunk in chunks:
            entities = _extract_entities_from_text(chunk.chunk_text)
            for ent in entities:
                ent_id = f"ent-{uuid.uuid4().hex[:8]}"
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO entities (id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (ent_id, ent["entity_type"], ent["name"], ent["value"],
                         chunk.id, doc.id, doc.investigation_id, ent["confidence"], ts),
                    )
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        created += 1
                except Exception as e:
                    logger.warning(f"Entity insert error: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Extracted {created} entities from {doc.id} ({len(chunks)} chunks)",
                     extra={"investigation_id": doc.investigation_id})
        return created

    def get_entities(
        self,
        entity_type: Optional[str] = None,
        investigation_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> list[Entity]:
        """Query entities with optional filters."""
        conn = self._get_conn()
        conditions = []
        params = []

        if entity_type:
            conditions.append("entity_type=?")
            params.append(entity_type)
        if investigation_id:
            conditions.append("investigation_id=?")
            params.append(investigation_id)
        if document_id:
            conditions.append("document_id=?")
            params.append(document_id)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at "
            f"FROM entities WHERE {where} ORDER BY entity_type, name",
            params,
        ).fetchall()
        conn.close()
        return [Entity(*r) for r in rows]

    def stats(self) -> dict:
        """Entity statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        by_type = conn.execute(
            "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


# Singleton
entity_extractor = EntityExtractor()
