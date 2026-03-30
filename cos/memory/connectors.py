"""COS external knowledge connectors — expand knowledge sources.

Registry of connectors for importing knowledge from external databases
(ChEMBL, PubChem, UniProt, etc.) into COS memory.

Usage:
    from cos.memory.connectors import connector_registry
    connector_registry.register("chembl", chembl_fetch_fn, domain="cheminformatics")
    results = connector_registry.fetch("chembl", query="CETP")
"""

import time
import uuid
import sqlite3
from dataclasses import dataclass
from typing import Callable, Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.connectors")


@dataclass
class ConnectorInfo:
    name: str
    domain: str
    description: str
    enabled: bool
    last_fetch_at: str
    fetch_count: int


class ConnectorRegistry:
    """Registry of external knowledge source connectors."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._connectors: dict[str, dict] = {}
        self._init_db()
        self._register_builtins()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS connector_log (
                    id TEXT PRIMARY KEY,
                    connector_name TEXT NOT NULL,
                    query TEXT NOT NULL,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clog_name ON connector_log(connector_name)")

    def register(self, name: str, fetch_fn: Callable, domain: str = "general",
                 description: str = "") -> None:
        """Register an external connector."""
        self._connectors[name] = {
            "fetch_fn": fetch_fn,
            "domain": domain,
            "description": description,
            "enabled": True,
            "last_fetch_at": "",
            "fetch_count": 0,
        }
        logger.info(f"Connector registered: {name} (domain={domain})")

    def fetch(self, name: str, query: str, investigation_id: str = "default") -> list[dict]:
        """Fetch data from a connector."""
        if name not in self._connectors:
            raise ValueError(f"Connector not found: {name}")

        conn_info = self._connectors[name]
        if not conn_info["enabled"]:
            raise ValueError(f"Connector disabled: {name}")

        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        log_id = f"fch-{uuid.uuid4().hex[:8]}"

        try:
            results = conn_info["fetch_fn"](query)
            conn_info["last_fetch_at"] = ts
            conn_info["fetch_count"] += 1

            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO connector_log (id, connector_name, query, result_count, status, investigation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (log_id, name, query, len(results), "success", investigation_id, ts),
                )

            logger.info(f"Connector '{name}' fetched {len(results)} results for '{query}'")
            return results

        except Exception as e:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO connector_log (id, connector_name, query, result_count, status, investigation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (log_id, name, query, 0, f"error: {str(e)[:100]}", investigation_id, ts),
                )
            raise

    def list_connectors(self) -> list[ConnectorInfo]:
        """List registered connectors."""
        return [
            ConnectorInfo(
                name=name, domain=c["domain"], description=c["description"],
                enabled=c["enabled"], last_fetch_at=c["last_fetch_at"],
                fetch_count=c["fetch_count"],
            )
            for name, c in self._connectors.items()
        ]

    def _register_builtins(self):
        """Register built-in stub connectors for supported databases."""
        def _stub_chembl(query: str) -> list[dict]:
            return [{"source": "chembl", "query": query, "note": "Stub: install chembl_webresource_client for live data"}]

        def _stub_pubchem(query: str) -> list[dict]:
            return [{"source": "pubchem", "query": query, "note": "Stub: use pubchempy for live data"}]

        def _stub_uniprot(query: str) -> list[dict]:
            return [{"source": "uniprot", "query": query, "note": "Stub: use requests + UniProt REST API for live data"}]

        self.register("chembl", _stub_chembl, domain="cheminformatics", description="ChEMBL compound/activity database")
        self.register("pubchem", _stub_pubchem, domain="cheminformatics", description="PubChem compound database")
        self.register("uniprot", _stub_uniprot, domain="biology", description="UniProt protein database")

    def stats(self) -> dict:
        conn = self._get_conn()
        total_fetches = conn.execute("SELECT COUNT(*) FROM connector_log").fetchone()[0]
        by_connector = conn.execute(
            "SELECT connector_name, COUNT(*), SUM(result_count) FROM connector_log GROUP BY connector_name"
        ).fetchall()
        conn.close()
        return {
            "registered": len(self._connectors),
            "total_fetches": total_fetches,
            "by_connector": {n: {"fetches": c, "results": r or 0} for n, c, r in by_connector},
        }


# Singleton
connector_registry = ConnectorRegistry()
