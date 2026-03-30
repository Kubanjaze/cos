"""COS semantic memory — structured concept definitions and domain knowledge.

Semantic memory answers "what do we know?" — facts, definitions, domain knowledge.
Distinct from episodic memory ("what happened?") in Phase 126.

Usage:
    from cos.memory.semantic import semantic_memory
    semantic_memory.define("CETP", "Cholesteryl ester transfer protein",
                          domain="cheminformatics", category="target", confidence=0.9)
    concept = semantic_memory.get("cetp")  # case-insensitive
    results = semantic_memory.search(domain="cheminformatics")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.semantic")


@dataclass
class Concept:
    id: str
    name: str
    definition: str
    domain: str
    category: str
    confidence: float
    source_ref: str
    investigation_id: str
    created_at: str
    updated_at: str


class SemanticMemory:
    """Structured concept store — semantic memory layer."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_lower TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT 'general',
                    category TEXT NOT NULL DEFAULT 'general',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    source_ref TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_concept_name ON concepts(name_lower)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_concept_domain ON concepts(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_concept_category ON concepts(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_concept_inv ON concepts(investigation_id)")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_concept_name_domain "
                "ON concepts(name_lower, domain)"
            )

    def define(
        self,
        name: str,
        definition: str,
        domain: str = "general",
        category: str = "general",
        confidence: float = 0.5,
        source_ref: str = "",
        investigation_id: str = "default",
    ) -> str:
        """Define or update a concept. Returns concept ID.

        If a concept with the same name+domain exists, updates it (upsert).
        """
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        name_lower = name.strip().lower()

        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id, confidence FROM concepts WHERE name_lower=? AND domain=?",
                (name_lower, domain),
            ).fetchone()

            if existing:
                # Upsert: update definition, bump confidence if higher
                concept_id = existing[0]
                new_confidence = max(existing[1], confidence)
                conn.execute(
                    "UPDATE concepts SET definition=?, category=?, confidence=?, "
                    "source_ref=?, investigation_id=?, updated_at=? WHERE id=?",
                    (definition, category, new_confidence, source_ref, investigation_id,
                     ts, concept_id),
                )
                logger.info(f"Concept updated: {name} (domain={domain})",
                            extra={"investigation_id": investigation_id})
            else:
                concept_id = f"con-{uuid.uuid4().hex[:8]}"
                conn.execute(
                    "INSERT INTO concepts (id, name, name_lower, definition, domain, category, "
                    "confidence, source_ref, investigation_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (concept_id, name.strip(), name_lower, definition, domain, category,
                     confidence, source_ref, investigation_id, ts, ts),
                )
                logger.info(f"Concept defined: {name} (domain={domain})",
                            extra={"investigation_id": investigation_id})

        return concept_id

    def get(self, name: str, domain: Optional[str] = None) -> Optional[Concept]:
        """Get a concept by name (case-insensitive). Optionally filter by domain."""
        conn = self._get_conn()
        name_lower = name.strip().lower()

        if domain:
            row = conn.execute(
                "SELECT id, name, definition, domain, category, confidence, source_ref, "
                "investigation_id, created_at, updated_at "
                "FROM concepts WHERE name_lower=? AND domain=?",
                (name_lower, domain),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, name, definition, domain, category, confidence, source_ref, "
                "investigation_id, created_at, updated_at "
                "FROM concepts WHERE name_lower=? ORDER BY confidence DESC LIMIT 1",
                (name_lower,),
            ).fetchone()

        conn.close()
        if not row:
            return None
        return Concept(*row)

    def search(
        self,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        text: Optional[str] = None,
        investigation_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Concept]:
        """Search concepts by domain, category, or text substring."""
        conn = self._get_conn()
        conditions = []
        params: list = []

        if domain:
            conditions.append("domain=?")
            params.append(domain)
        if category:
            conditions.append("category=?")
            params.append(category)
        if text:
            conditions.append("(name_lower LIKE ? OR definition LIKE ?)")
            text_pattern = f"%{text.lower()}%"
            params.extend([text_pattern, text_pattern])
        if investigation_id:
            conditions.append("investigation_id=?")
            params.append(investigation_id)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"SELECT id, name, definition, domain, category, confidence, source_ref, "
            f"investigation_id, created_at, updated_at "
            f"FROM concepts WHERE {where} ORDER BY confidence DESC, name_lower LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [Concept(*r) for r in rows]

    def update(
        self,
        name: str,
        domain: str = "general",
        definition: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        source_ref: Optional[str] = None,
    ) -> bool:
        """Update specific fields of an existing concept. Returns True if found."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        name_lower = name.strip().lower()

        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM concepts WHERE name_lower=? AND domain=?",
                (name_lower, domain),
            ).fetchone()
            if not existing:
                return False

            updates = ["updated_at=?"]
            params: list = [ts]

            if definition is not None:
                updates.append("definition=?")
                params.append(definition)
            if category is not None:
                updates.append("category=?")
                params.append(category)
            if confidence is not None:
                updates.append("confidence=?")
                params.append(confidence)
            if source_ref is not None:
                updates.append("source_ref=?")
                params.append(source_ref)

            params.append(existing[0])
            conn.execute(
                f"UPDATE concepts SET {', '.join(updates)} WHERE id=?",
                params,
            )

        logger.info(f"Concept updated: {name} (domain={domain})")
        return True

    def list_concepts(
        self,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[Concept]:
        """List all concepts with optional filters."""
        return self.search(domain=domain, category=category, limit=limit)

    def stats(self) -> dict:
        """Return concept statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        avg_conf = conn.execute(
            "SELECT COALESCE(AVG(confidence), 0) FROM concepts"
        ).fetchone()[0]
        by_domain = conn.execute(
            "SELECT domain, COUNT(*) FROM concepts GROUP BY domain ORDER BY COUNT(*) DESC"
        ).fetchall()
        by_category = conn.execute(
            "SELECT category, COUNT(*) FROM concepts GROUP BY category ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "avg_confidence": round(avg_conf, 3),
            "by_domain": {d: c for d, c in by_domain},
            "by_category": {cat: c for cat, c in by_category},
        }


# Singleton
semantic_memory = SemanticMemory()
