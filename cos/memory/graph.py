"""COS knowledge graph — unified query layer over entities + relations.

Provides graph semantics (neighbors, paths, subgraphs) over the existing
entities table (Phase 123) and entity_relations table (Phase 124).

Usage:
    from cos.memory.graph import knowledge_graph
    neighbors = knowledge_graph.neighbors("benz_001_F")
    path = knowledge_graph.path("benz_001_F", "benz")
    sub = knowledge_graph.subgraph("CETP", depth=2)
"""

import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.graph")


@dataclass
class GraphNode:
    name: str
    entity_type: str
    document_id: str
    confidence: float


@dataclass
class GraphEdge:
    source: str
    relation_type: str
    target: str
    confidence: float
    document_id: str


class KnowledgeGraph:
    """Graph query layer over entities + entity_relations tables."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _build_adjacency(self, conn: sqlite3.Connection) -> dict[str, list[tuple[str, str, str]]]:
        """Build adjacency list from entity_relations. Returns {entity: [(neighbor, rel_type, doc_id), ...]}."""
        adj: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        rows = conn.execute(
            "SELECT source_entity, relation_type, target_value, document_id FROM entity_relations"
        ).fetchall()
        for source, rel_type, target, doc_id in rows:
            adj[source].append((target, rel_type, doc_id))
            adj[target].append((source, rel_type, doc_id))  # bidirectional
        return adj

    def neighbors(self, entity_name: str, relation_type: Optional[str] = None) -> list[dict]:
        """Find all entities connected to the given entity (1-hop)."""
        conn = self._get_conn()

        conditions = ["source_entity=?"]
        params: list = [entity_name]
        if relation_type:
            conditions.append("relation_type=?")
            params.append(relation_type)

        # Outgoing edges
        where = " AND ".join(conditions)
        outgoing = conn.execute(
            f"SELECT target_value, relation_type, confidence, document_id "
            f"FROM entity_relations WHERE {where}",
            params,
        ).fetchall()

        # Incoming edges (where this entity is the target)
        in_conditions = ["target_value=?"]
        in_params: list = [entity_name]
        if relation_type:
            in_conditions.append("relation_type=?")
            in_params.append(relation_type)

        in_where = " AND ".join(in_conditions)
        incoming = conn.execute(
            f"SELECT source_entity, relation_type, confidence, document_id "
            f"FROM entity_relations WHERE {in_where}",
            in_params,
        ).fetchall()

        conn.close()

        results = []
        seen = set()
        for target, rel, conf, doc_id in outgoing:
            key = (target, rel)
            if key not in seen:
                seen.add(key)
                results.append({
                    "entity": target, "relation": rel, "direction": "outgoing",
                    "confidence": conf, "document_id": doc_id,
                })
        for source, rel, conf, doc_id in incoming:
            key = (source, rel)
            if key not in seen:
                seen.add(key)
                results.append({
                    "entity": source, "relation": rel, "direction": "incoming",
                    "confidence": conf, "document_id": doc_id,
                })

        return results

    def path(
        self, source: str, target: str, max_depth: int = 5
    ) -> Optional[list[dict]]:
        """BFS shortest path between two entities. Returns list of steps or None."""
        conn = self._get_conn()
        adj = self._build_adjacency(conn)
        conn.close()

        if source not in adj and target not in adj:
            return None

        # BFS
        queue: deque[tuple[str, list[dict]]] = deque()
        queue.append((source, []))
        visited = {source}

        while queue:
            current, path_so_far = queue.popleft()
            if len(path_so_far) >= max_depth:
                continue

            for neighbor, rel_type, doc_id in adj.get(current, []):
                if neighbor == target:
                    return path_so_far + [{
                        "from": current, "to": neighbor,
                        "relation": rel_type, "document_id": doc_id,
                    }]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path_so_far + [{
                        "from": current, "to": neighbor,
                        "relation": rel_type, "document_id": doc_id,
                    }]))

        return None  # No path found

    def subgraph(self, entity_name: str, depth: int = 2) -> dict:
        """Extract N-hop neighborhood as nodes + edges."""
        conn = self._get_conn()
        adj = self._build_adjacency(conn)
        conn.close()

        nodes: set[str] = set()
        edges: list[dict] = []
        edge_set: set[tuple[str, str, str]] = set()

        # BFS to collect neighborhood
        queue: deque[tuple[str, int]] = deque()
        queue.append((entity_name, 0))
        nodes.add(entity_name)

        while queue:
            current, d = queue.popleft()
            if d >= depth:
                continue
            for neighbor, rel_type, doc_id in adj.get(current, []):
                edge_key = (min(current, neighbor), max(current, neighbor), rel_type)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": current, "target": neighbor,
                        "relation": rel_type, "document_id": doc_id,
                    })
                if neighbor not in nodes:
                    nodes.add(neighbor)
                    queue.append((neighbor, d + 1))

        return {
            "center": entity_name,
            "depth": depth,
            "nodes": sorted(nodes),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def query(
        self,
        entity_type: Optional[str] = None,
        relation_type: Optional[str] = None,
        target: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Flexible graph query with filters."""
        conn = self._get_conn()

        conditions: list[str] = []
        params: list = []
        use_join = entity_type is not None

        if relation_type:
            prefix = "r." if use_join else ""
            conditions.append(f"{prefix}relation_type=?")
            params.append(relation_type)
        if target:
            prefix = "r." if use_join else ""
            conditions.append(f"{prefix}target_value=?")
            params.append(target)
        if entity_type:
            conditions.append("e.entity_type=?")
            params.append(entity_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        if use_join:
            rows = conn.execute(
                f"SELECT r.source_entity, r.relation_type, r.target_value, r.confidence, r.document_id "
                f"FROM entity_relations r "
                f"JOIN entities e ON r.source_entity = e.name AND r.document_id = e.document_id "
                f"WHERE {where} ORDER BY r.source_entity LIMIT ?",
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT source_entity, relation_type, target_value, confidence, document_id "
                f"FROM entity_relations WHERE {where} ORDER BY source_entity LIMIT ?",
                params,
            ).fetchall()

        conn.close()
        return [
            {"source": r[0], "relation": r[1], "target": r[2],
             "confidence": r[3], "document_id": r[4]}
            for r in rows
        ]

    def connected_components(self) -> list[list[str]]:
        """Find connected components in the graph."""
        conn = self._get_conn()
        adj = self._build_adjacency(conn)
        conn.close()

        visited: set[str] = set()
        components: list[list[str]] = []

        for node in adj:
            if node not in visited:
                component: list[str] = []
                queue: deque[str] = deque([node])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.append(current)
                    for neighbor, _, _ in adj[current]:
                        if neighbor not in visited:
                            queue.append(neighbor)
                components.append(sorted(component))

        # Sort by size descending
        components.sort(key=len, reverse=True)
        return components

    def stats(self) -> dict:
        """Graph statistics: nodes, edges, avg degree, components."""
        conn = self._get_conn()
        node_count = conn.execute("SELECT COUNT(DISTINCT name) FROM entities").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        conn.close()

        components = self.connected_components()
        avg_degree = round(2 * edge_count / node_count, 2) if node_count > 0 else 0

        return {
            "nodes": node_count,
            "edges": edge_count,
            "avg_degree": avg_degree,
            "components": len(components),
            "largest_component": len(components[0]) if components else 0,
        }


# Singleton
knowledge_graph = KnowledgeGraph()
