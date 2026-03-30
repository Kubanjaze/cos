# Phase 129 — Knowledge Graph Database Integration

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Provide a unified graph query layer over the existing entity and relation tables (Phases 123-124). Supports traversal, neighbor lookup, path finding, and subgraph extraction — enabling "query relationships" without raw SQL.

CLI: `python -m cos graph {neighbors,path,subgraph,stats}`

Outputs: Graph query results from existing `entities` + `entity_relations` tables (no new DB tables)

## Logic
1. `KnowledgeGraph` class wraps entities + entity_relations tables with graph semantics
2. `neighbors(entity_name)` — find all entities connected by a relation (1-hop)
3. `path(source, target, max_depth)` — BFS shortest path between two entities
4. `subgraph(entity_name, depth)` — extract N-hop neighborhood as nodes + edges
5. `query(entity_type, relation_type, target)` — flexible filter-based graph query
6. `connected_components()` — group entities into connected clusters
7. `stats()` — node count, edge count, avg degree, component count

## Key Concepts
- **No new DB tables**: queries existing `entities` + `entity_relations` tables
- **Graph semantics over relational data**: entities are nodes, relations are edges
- **BFS traversal**: path finding uses breadth-first search with depth limit
- **Bidirectional edges**: treats relations as undirected for traversal (A→B means B is neighbor of A too)
- **Subgraph extraction**: returns dict with nodes[] and edges[] for downstream visualization (Phase 140)

## Verification Checklist
- [ ] `neighbors("benz_001_F")` returns scaffold + activity relations
- [ ] `path("benz_001_F", "benz")` finds compound → scaffold path
- [ ] `subgraph("CETP", depth=2)` returns multi-hop neighborhood
- [ ] `query(relation_type="belongs_to_scaffold")` returns all scaffold memberships
- [ ] `connected_components()` returns cluster groupings
- [ ] `stats()` shows node/edge/degree/component counts
- [ ] CLI: graph neighbors/path/subgraph/stats all work

## Risks
- Performance on large graphs: BFS with depth limit mitigates
- Entity name matching: must handle exact names from existing data
- No new tables means no graph-specific indexes — acceptable at current scale
