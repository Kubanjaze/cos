"""COS domain adapters — specialized reasoning per domain. Phase 157."""

from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.domain_adapters")


class DomainAdapter:
    """Base domain adapter."""
    name: str = "generic"
    domain: str = "general"

    def analyze(self, query: str) -> dict:
        return {"adapter": self.name, "query": query, "result": "Generic analysis"}


class CheminformaticsAdapter(DomainAdapter):
    """Adapter for cheminformatics domain."""
    name = "cheminformatics"
    domain = "cheminformatics"

    def analyze(self, query: str) -> dict:
        import sqlite3
        conn = sqlite3.connect(settings.db_path)
        scaffolds = conn.execute(
            "SELECT DISTINCT target_value FROM entity_relations WHERE relation_type='belongs_to_scaffold'"
        ).fetchall()
        compounds = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type='compound'").fetchone()[0]
        activities = conn.execute("SELECT COUNT(*) FROM entity_relations WHERE relation_type='has_activity'").fetchone()[0]
        conn.close()
        return {
            "adapter": self.name, "query": query,
            "scaffolds": len(scaffolds), "compounds": compounds, "activities": activities,
            "suggestion": f"Analyze SAR across {len(scaffolds)} scaffolds with {activities} activity points",
        }


class ClinicalAdapter(DomainAdapter):
    """Adapter for clinical domain."""
    name = "clinical"
    domain = "clinical"

    def analyze(self, query: str) -> dict:
        import sqlite3
        conn = sqlite3.connect(settings.db_path)
        concepts = conn.execute(
            "SELECT COUNT(*) FROM concepts WHERE domain='clinical'"
        ).fetchone()[0]
        conn.close()
        return {
            "adapter": self.name, "query": query, "concepts": concepts,
            "suggestion": f"Clinical domain has {concepts} concept(s) — consider expanding",
        }


class DomainAdapterRegistry:
    """Registry of domain-specific reasoning adapters."""

    def __init__(self):
        self._adapters: dict[str, DomainAdapter] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register(CheminformaticsAdapter())
        self.register(ClinicalAdapter())

    def register(self, adapter: DomainAdapter):
        self._adapters[adapter.name] = adapter

    def get(self, domain: str) -> Optional[DomainAdapter]:
        return self._adapters.get(domain)

    def analyze(self, domain: str, query: str) -> dict:
        adapter = self.get(domain)
        if not adapter:
            return DomainAdapter().analyze(query)
        return adapter.analyze(query)

    def list_adapters(self) -> list[dict]:
        return [{"name": a.name, "domain": a.domain} for a in self._adapters.values()]

    def stats(self) -> dict:
        return {"registered_adapters": len(self._adapters),
                "adapters": [a.name for a in self._adapters.values()]}


domain_adapter_registry = DomainAdapterRegistry()
