"""COS cross-domain linking — connect knowledge across domains.

Links concepts, entities, and relations across domain boundaries to enable
knowledge transfer (e.g., cheminformatics ↔ clinical).

Usage:
    from cos.memory.crossdomain import cross_linker
    n = cross_linker.discover_links()
    links = cross_linker.get_links(domain="cheminformatics")
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.crossdomain")


@dataclass
class CrossLink:
    id: str
    source_type: str
    source_id: str
    source_domain: str
    target_type: str
    target_id: str
    target_domain: str
    link_type: str
    confidence: float
    created_at: str


class CrossDomainLinker:
    """Discovers and manages cross-domain knowledge links."""

    _COLS = (
        "id, source_type, source_id, source_domain, target_type, target_id, "
        "target_domain, link_type, confidence, created_at"
    )

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_links (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_domain TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_domain TEXT NOT NULL,
                    link_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, target_id, link_type)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_source ON cross_links(source_domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_target ON cross_links(target_domain)")

    def discover_links(self) -> int:
        """Auto-discover cross-domain links from shared concept names."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        # Find concepts with same name across different domains
        rows = conn.execute("""
            SELECT a.id, a.domain, b.id, b.domain, a.name
            FROM concepts a JOIN concepts b
            ON a.name_lower = b.name_lower AND a.domain < b.domain
        """).fetchall()

        for a_id, a_dom, b_id, b_dom, name in rows:
            lid = f"cl-{uuid.uuid4().hex[:8]}"
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO cross_links "
                    "(id, source_type, source_id, source_domain, target_type, target_id, "
                    "target_domain, link_type, confidence, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (lid, "concept", a_id, a_dom, "concept", b_id, b_dom,
                     "same_concept", 0.8, ts),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    created += 1
            except Exception:
                pass

        conn.commit()
        conn.close()
        logger.info(f"Discovered {created} cross-domain links")
        return created

    def add_link(self, source_type: str, source_id: str, source_domain: str,
                 target_type: str, target_id: str, target_domain: str,
                 link_type: str, confidence: float = 0.5) -> str:
        """Manually add a cross-domain link."""
        lid = f"cl-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO cross_links "
                "(id, source_type, source_id, source_domain, target_type, target_id, "
                "target_domain, link_type, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lid, source_type, source_id, source_domain, target_type, target_id,
                 target_domain, link_type, confidence, ts),
            )
        return lid

    def get_links(self, domain: Optional[str] = None, link_type: Optional[str] = None,
                  limit: int = 50) -> list[CrossLink]:
        """Get cross-domain links with optional filters."""
        conn = self._get_conn()
        conditions: list[str] = []
        params: list = []
        if domain:
            conditions.append("(source_domain=? OR target_domain=?)")
            params.extend([domain, domain])
        if link_type:
            conditions.append("link_type=?")
            params.append(link_type)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = conn.execute(
            f"SELECT {self._COLS} FROM cross_links WHERE {where} ORDER BY confidence DESC LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [CrossLink(*r) for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM cross_links").fetchone()[0]
        by_type = conn.execute(
            "SELECT link_type, COUNT(*) FROM cross_links GROUP BY link_type"
        ).fetchall()
        domains = conn.execute(
            "SELECT DISTINCT source_domain FROM cross_links UNION SELECT DISTINCT target_domain FROM cross_links"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "by_type": {t: c for t, c in by_type},
            "domains_linked": [d[0] for d in domains],
        }


# Singleton
cross_linker = CrossDomainLinker()
