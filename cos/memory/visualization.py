"""COS memory visualization — graph + cluster views of knowledge.

Generates text-based and data-export visualizations of the knowledge graph,
domain clusters, and memory structure.

Usage:
    from cos.memory.visualization import memory_viz
    text = memory_viz.graph_ascii("benz", depth=1)
    export = memory_viz.export_graph(format="json")
"""

import json
import sqlite3
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.visualization")


class MemoryVisualization:
    """Generates visualizations of COS memory structure."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def graph_ascii(self, entity_name: str, depth: int = 1) -> str:
        """Generate ASCII tree view of entity neighborhood."""
        from cos.memory.graph import knowledge_graph
        sub = knowledge_graph.subgraph(entity_name, depth=depth)

        lines = [f"[{entity_name}]"]
        # Group edges by source
        by_source: dict[str, list[tuple[str, str]]] = {}
        for e in sub["edges"]:
            src = e["source"]
            if src not in by_source:
                by_source[src] = []
            by_source[src].append((e["relation"], e["target"]))

        # Build tree from center
        seen = {entity_name}
        self._build_tree(lines, entity_name, by_source, sub["edges"], seen, depth, "")

        return "\n".join(lines)

    def _build_tree(self, lines, node, by_source, all_edges, seen, remaining, prefix):
        if remaining <= 0:
            return
        # Find neighbors
        neighbors = []
        for e in all_edges:
            if e["source"] == node and e["target"] not in seen:
                neighbors.append((e["relation"], e["target"]))
            elif e["target"] == node and e["source"] not in seen:
                neighbors.append((e["relation"], e["source"]))

        for i, (rel, neighbor) in enumerate(neighbors):
            is_last = i == len(neighbors) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}--[{rel}]--> {neighbor}")
            seen.add(neighbor)
            next_prefix = prefix + ("    " if is_last else "│   ")
            self._build_tree(lines, neighbor, by_source, all_edges, seen, remaining - 1, next_prefix)

    def domain_clusters(self) -> dict:
        """Show concepts grouped by domain."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT domain, name, confidence FROM concepts ORDER BY domain, confidence DESC"
        ).fetchall()
        conn.close()

        clusters: dict[str, list[dict]] = {}
        for domain, name, conf in rows:
            if domain not in clusters:
                clusters[domain] = []
            clusters[domain].append({"name": name, "confidence": conf})

        return clusters

    def entity_type_distribution(self) -> dict:
        """Show entity distribution by type."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()
        return {t: c for t, c in rows}

    def export_graph(self, format: str = "json") -> str:
        """Export full knowledge graph as JSON (nodes + edges)."""
        conn = self._get_conn()

        nodes = []
        rows = conn.execute("SELECT DISTINCT name, entity_type FROM entities").fetchall()
        for name, etype in rows:
            nodes.append({"id": name, "type": etype, "group": "entity"})

        # Add concept nodes
        rows = conn.execute("SELECT name, domain FROM concepts").fetchall()
        for name, domain in rows:
            nodes.append({"id": name, "type": "concept", "group": domain})

        edges = []
        rows = conn.execute(
            "SELECT source_entity, relation_type, target_value FROM entity_relations"
        ).fetchall()
        for source, rel, target in rows:
            edges.append({"source": source, "target": target, "relation": rel})

        conn.close()

        data = {"nodes": nodes, "edges": edges,
                "node_count": len(nodes), "edge_count": len(edges)}

        if format == "json":
            return json.dumps(data, indent=2)
        return json.dumps(data)

    def memory_map(self) -> str:
        """Generate text summary of entire memory structure."""
        conn = self._get_conn()
        lines = ["COS Memory Map", "=" * 40]

        tables = [
            ("documents", "Documents"), ("document_chunks", "Chunks"),
            ("entities", "Entities"), ("entity_relations", "Relations"),
            ("concepts", "Concepts"), ("episodes", "Episodes"),
            ("procedures", "Procedures"), ("provenance", "Provenance links"),
            ("conflicts", "Conflicts"), ("memory_scores", "Scores"),
        ]

        for table, label in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                lines.append(f"  {label:25s} {count:>6}")
            except Exception:
                lines.append(f"  {label:25s}   N/A")

        conn.close()
        return "\n".join(lines)

    def stats(self) -> dict:
        conn = self._get_conn()
        entities = conn.execute("SELECT COUNT(DISTINCT name) FROM entities").fetchone()[0]
        relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        conn.close()
        return {"entities": entities, "relations": relations, "concepts": concepts}


# Singleton
memory_viz = MemoryVisualization()
