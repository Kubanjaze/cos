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
        """Register built-in connectors — ChEMBL is live, others are stubs."""

        def _chembl_fetch(query: str) -> list[dict]:
            """Fetch bioactivity data from ChEMBL REST API for a target name."""
            import requests

            # Step 1: Search for target
            search_url = f"https://www.ebi.ac.uk/chembl/api/data/target/search.json?q={query}&limit=5"
            resp = requests.get(search_url, timeout=15)
            if resp.status_code != 200:
                return [{"error": f"ChEMBL search failed: {resp.status_code}"}]

            targets = resp.json().get("targets", [])
            if not targets:
                return [{"error": f"No targets found for '{query}'"}]

            # Pick first single protein target
            target_chembl_id = None
            target_name = ""
            for t in targets:
                if t.get("target_type") == "SINGLE PROTEIN":
                    target_chembl_id = t["target_chembl_id"]
                    target_name = t.get("pref_name", query)
                    break
            if not target_chembl_id:
                target_chembl_id = targets[0]["target_chembl_id"]
                target_name = targets[0].get("pref_name", query)

            # Step 2: Fetch bioactivities (IC50/Ki in nM)
            act_url = (f"https://www.ebi.ac.uk/chembl/api/data/activity.json?"
                       f"target_chembl_id={target_chembl_id}&standard_type__in=IC50,Ki&limit=100"
                       f"&standard_units=nM&standard_relation==")
            resp = requests.get(act_url, timeout=20)
            if resp.status_code != 200:
                return [{"error": f"ChEMBL activity fetch failed: {resp.status_code}"}]

            activities = resp.json().get("activities", [])
            results = []
            seen = set()

            for act in activities:
                mol_id = act.get("molecule_chembl_id", "")
                smiles = act.get("canonical_smiles", "")
                std_value = act.get("standard_value")
                std_type = act.get("standard_type", "IC50")
                mol_name = act.get("molecule_pref_name") or mol_id

                if not mol_id or not std_value or mol_id in seen:
                    continue
                seen.add(mol_id)

                try:
                    value_nm = float(std_value)
                    # Convert to pIC50: -log10(IC50 in M) = -log10(IC50_nM * 1e-9)
                    import math
                    if value_nm > 0:
                        pic50 = round(-math.log10(value_nm * 1e-9), 2)
                    else:
                        pic50 = None
                except (ValueError, TypeError):
                    pic50 = None

                results.append({
                    "compound_name": mol_name,
                    "chembl_id": mol_id,
                    "smiles": smiles,
                    "activity_type": std_type,
                    "activity_value_nM": std_value,
                    "pic50": pic50,
                    "target": target_name,
                    "target_chembl_id": target_chembl_id,
                    "source": "chembl",
                })

            logger.info(f"ChEMBL: fetched {len(results)} compounds for '{query}' ({target_chembl_id})")
            return results

        def _stub_pubchem(query: str) -> list[dict]:
            return [{"source": "pubchem", "query": query, "note": "Stub: use pubchempy for live data"}]

        def _stub_uniprot(query: str) -> list[dict]:
            return [{"source": "uniprot", "query": query, "note": "Stub: use requests + UniProt REST API for live data"}]

        self.register("chembl", _chembl_fetch, domain="cheminformatics", description="ChEMBL compound/activity database (LIVE)")
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
