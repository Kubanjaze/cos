"""COS conflict detection — find contradictions in memory.

Scans concepts, entities, and relations for inconsistencies: duplicate
definitions, contradictory values, confidence disagreements.

Usage:
    from cos.memory.conflicts import conflict_detector
    n = conflict_detector.scan()
    conflicts = conflict_detector.list_conflicts(status="open")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.conflicts")


@dataclass
class Conflict:
    id: str
    conflict_type: str
    item_a_type: str
    item_a_id: str
    item_b_type: str
    item_b_id: str
    description: str
    severity: str
    status: str
    resolution: str
    investigation_id: str
    created_at: str
    resolved_at: str


class ConflictDetector:
    """Detects contradictions across COS memory."""

    _COLS = (
        "id, conflict_type, item_a_type, item_a_id, item_b_type, item_b_id, "
        "description, severity, status, resolution, investigation_id, created_at, resolved_at"
    )

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conflicts (
                    id TEXT PRIMARY KEY,
                    conflict_type TEXT NOT NULL,
                    item_a_type TEXT NOT NULL,
                    item_a_id TEXT NOT NULL,
                    item_b_type TEXT NOT NULL,
                    item_b_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'open',
                    resolution TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conf_type ON conflicts(conflict_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conf_status ON conflicts(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conf_sev ON conflicts(severity)")

    def scan(self, investigation_id: str = "default") -> int:
        """Scan memory for conflicts. Returns number of new conflicts found."""
        created = 0
        created += self._scan_duplicate_concepts()
        created += self._scan_contradictory_relations()
        created += self._scan_confidence_disagreements()
        logger.info(f"Conflict scan complete: {created} new conflicts found")
        return created

    def _scan_duplicate_concepts(self) -> int:
        """Find concepts with same name_lower but different definitions across domains."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        # Find concept names that appear in multiple domains with different definitions
        rows = conn.execute("""
            SELECT a.id, a.name, a.domain, a.definition, b.id, b.name, b.domain, b.definition
            FROM concepts a JOIN concepts b
            ON a.name_lower = b.name_lower AND a.domain < b.domain
            WHERE a.definition != b.definition
        """).fetchall()

        for a_id, a_name, a_dom, a_def, b_id, b_name, b_dom, b_def in rows:
            desc = f"Concept '{a_name}' has different definitions in domains '{a_dom}' vs '{b_dom}'"
            created += self._insert_conflict(
                conn, "duplicate_concept", "concept", a_id, "concept", b_id,
                desc, "medium", "default", ts
            )

        conn.commit()
        conn.close()
        return created

    def _scan_contradictory_relations(self) -> int:
        """Find entities with conflicting activity values."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        # Find same entity with different activity values
        rows = conn.execute("""
            SELECT a.id, a.source_entity, a.target_value, b.id, b.target_value
            FROM entity_relations a JOIN entity_relations b
            ON a.source_entity = b.source_entity
            AND a.relation_type = b.relation_type
            AND a.relation_type = 'has_activity'
            AND a.id < b.id
            AND a.target_value != b.target_value
        """).fetchall()

        for a_id, entity, a_val, b_id, b_val in rows:
            desc = f"Entity '{entity}' has conflicting activities: {a_val} vs {b_val}"
            created += self._insert_conflict(
                conn, "contradictory_relation", "relation", a_id, "relation", b_id,
                desc, "high", "default", ts
            )

        conn.commit()
        conn.close()
        return created

    def _scan_confidence_disagreements(self) -> int:
        """Find low-confidence concepts that contradict high-confidence ones."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        # Find concepts where confidence differs significantly (>0.5 gap) for same name
        rows = conn.execute("""
            SELECT a.id, a.name, a.domain, a.confidence, b.id, b.domain, b.confidence
            FROM concepts a JOIN concepts b
            ON a.name_lower = b.name_lower AND a.id < b.id
            WHERE ABS(a.confidence - b.confidence) > 0.5
        """).fetchall()

        for a_id, name, a_dom, a_conf, b_id, b_dom, b_conf in rows:
            desc = f"Concept '{name}' has confidence disagreement: {a_conf:.2f} ({a_dom}) vs {b_conf:.2f} ({b_dom})"
            created += self._insert_conflict(
                conn, "confidence_disagreement", "concept", a_id, "concept", b_id,
                desc, "low", "default", ts
            )

        conn.commit()
        conn.close()
        return created

    def _insert_conflict(self, conn, conflict_type, a_type, a_id, b_type, b_id,
                         description, severity, investigation_id, ts) -> int:
        cid = f"cfl-{uuid.uuid4().hex[:8]}"
        try:
            # Check for existing identical conflict
            existing = conn.execute(
                "SELECT id FROM conflicts WHERE item_a_id=? AND item_b_id=? AND conflict_type=? AND status='open'",
                (a_id, b_id, conflict_type),
            ).fetchone()
            if existing:
                return 0

            conn.execute(
                "INSERT INTO conflicts (id, conflict_type, item_a_type, item_a_id, "
                "item_b_type, item_b_id, description, severity, status, resolution, "
                "investigation_id, created_at, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, conflict_type, a_type, a_id, b_type, b_id,
                 description, severity, "open", "", investigation_id, ts, ""),
            )
            return 1
        except Exception:
            return 0

    def list_conflicts(
        self,
        status: Optional[str] = None,
        conflict_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> list[Conflict]:
        """List conflicts with optional filters."""
        conn = self._get_conn()
        conditions: list[str] = []
        params: list = []

        if status:
            conditions.append("status=?")
            params.append(status)
        if conflict_type:
            conditions.append("conflict_type=?")
            params.append(conflict_type)
        if severity:
            conditions.append("severity=?")
            params.append(severity)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"SELECT {self._COLS} FROM conflicts WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [Conflict(*r) for r in rows]

    def resolve(self, conflict_id: str, resolution: str) -> bool:
        """Mark a conflict as resolved. Returns True if found."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM conflicts WHERE id=? OR id LIKE ?",
                (conflict_id, conflict_id + "%"),
            ).fetchone()
            if not existing:
                return False
            conn.execute(
                "UPDATE conflicts SET status='resolved', resolution=?, resolved_at=? WHERE id=?",
                (resolution, ts, existing[0]),
            )
        logger.info(f"Conflict resolved: {conflict_id}")
        return True

    def stats(self) -> dict:
        """Conflict statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0]
        by_type = conn.execute(
            "SELECT conflict_type, COUNT(*) FROM conflicts GROUP BY conflict_type"
        ).fetchall()
        by_severity = conn.execute(
            "SELECT severity, COUNT(*) FROM conflicts GROUP BY severity"
        ).fetchall()
        by_status = conn.execute(
            "SELECT status, COUNT(*) FROM conflicts GROUP BY status"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "by_type": {t: c for t, c in by_type},
            "by_severity": {s: c for s, c in by_severity},
            "by_status": {s: c for s, c in by_status},
        }


# Singleton
conflict_detector = ConflictDetector()
