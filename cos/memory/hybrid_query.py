"""COS hybrid query engine — vector + graph + keyword search combined.

Merges results from semantic search (embeddings), graph traversal, and
keyword text search into a single ranked result set.

Usage:
    from cos.memory.hybrid_query import hybrid_engine
    results = hybrid_engine.search("CETP inhibitor activity")
"""

import sqlite3
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.hybrid_query")

# Weights for result fusion
W_VECTOR = 0.4
W_KEYWORD = 0.35
W_GRAPH = 0.25


class HybridQueryEngine:
    """Combines vector, keyword, and graph search."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def search(
        self,
        query: str,
        top_k: int = 10,
        use_vector: bool = True,
        use_keyword: bool = True,
        use_graph: bool = True,
    ) -> list[dict]:
        """Run hybrid search and return fused results."""
        results: dict[str, dict] = {}

        if use_keyword:
            for r in self._keyword_search(query, top_k * 2):
                key = f"{r['type']}:{r['id']}"
                if key not in results:
                    results[key] = {"type": r["type"], "id": r["id"], "name": r["name"],
                                    "text": r["text"], "scores": {}}
                results[key]["scores"]["keyword"] = r["score"]

        if use_vector:
            for r in self._vector_search(query, top_k * 2):
                key = f"{r['type']}:{r['id']}"
                if key not in results:
                    results[key] = {"type": r["type"], "id": r["id"], "name": r.get("name", ""),
                                    "text": r["text"], "scores": {}}
                results[key]["scores"]["vector"] = r["score"]

        if use_graph:
            for r in self._graph_search(query, top_k * 2):
                key = f"{r['type']}:{r['id']}"
                if key not in results:
                    results[key] = {"type": r["type"], "id": r["id"], "name": r.get("name", ""),
                                    "text": r.get("text", ""), "scores": {}}
                results[key]["scores"]["graph"] = r["score"]

        # Compute fused score
        for r in results.values():
            scores = r["scores"]
            r["fused_score"] = round(
                W_VECTOR * scores.get("vector", 0) +
                W_KEYWORD * scores.get("keyword", 0) +
                W_GRAPH * scores.get("graph", 0), 4
            )
            r["sources"] = list(scores.keys())

        ranked = sorted(results.values(), key=lambda x: x["fused_score"], reverse=True)
        return ranked[:top_k]

    def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """Search concepts and document chunks by text."""
        conn = self._get_conn()
        results = []
        pattern = f"%{query.lower()}%"

        # Search concepts
        rows = conn.execute(
            "SELECT id, name, definition, domain FROM concepts WHERE name_lower LIKE ? OR definition LIKE ? LIMIT ?",
            (pattern, pattern, limit),
        ).fetchall()
        for cid, name, defn, domain in rows:
            results.append({"type": "concept", "id": cid, "name": name,
                           "text": defn[:100], "score": 1.0})

        # Search document chunks
        rows = conn.execute(
            "SELECT c.id, d.title, c.chunk_text FROM document_chunks c "
            "JOIN documents d ON c.document_id = d.id "
            "WHERE c.chunk_text LIKE ? LIMIT ?",
            (pattern, limit),
        ).fetchall()
        for chk_id, title, text in rows:
            results.append({"type": "chunk", "id": chk_id, "name": title,
                           "text": text[:100], "score": 0.8})

        # Search entities
        rows = conn.execute(
            "SELECT id, name, entity_type FROM entities WHERE name LIKE ? LIMIT ?",
            (pattern, limit),
        ).fetchall()
        for eid, name, etype in rows:
            results.append({"type": "entity", "id": eid, "name": name,
                           "text": f"{etype}: {name}", "score": 0.9})

        conn.close()
        return results

    def _vector_search(self, query: str, limit: int) -> list[dict]:
        """Semantic search via embeddings."""
        try:
            from cos.memory.embeddings import embedding_pipeline
            raw = embedding_pipeline.search(query, top_k=limit)
            return [
                {"type": "chunk", "id": r.get("chunk_id", ""), "name": r.get("document_id", ""),
                 "text": r.get("text", "")[:100], "score": r.get("similarity", 0)}
                for r in raw
            ]
        except Exception:
            return []

    def _graph_search(self, query: str, limit: int) -> list[dict]:
        """Search graph by entity name match + neighbor expansion."""
        conn = self._get_conn()
        results = []
        pattern = f"%{query}%"

        # Find matching entities in relations
        rows = conn.execute(
            "SELECT DISTINCT source_entity, relation_type, target_value "
            "FROM entity_relations WHERE source_entity LIKE ? LIMIT ?",
            (pattern, limit),
        ).fetchall()
        for source, rel, target in rows:
            results.append({"type": "relation", "id": f"{source}-{rel}-{target}",
                           "name": source, "text": f"{source} {rel} {target}", "score": 0.7})

        conn.close()
        return results

    def stats(self) -> dict:
        """Query engine stats."""
        conn = self._get_conn()
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        try:
            embeddings = conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
        except Exception:
            embeddings = 0
        conn.close()
        return {
            "searchable_concepts": concepts,
            "searchable_chunks": chunks,
            "searchable_entities": entities,
            "searchable_relations": relations,
            "vector_embeddings": embeddings,
            "weights": {"vector": W_VECTOR, "keyword": W_KEYWORD, "graph": W_GRAPH},
        }


# Singleton
hybrid_engine = HybridQueryEngine()
