# Phase 129 — Knowledge Graph Database Integration

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Provide a unified graph query layer over the existing entity and relation tables (Phases 123-124). Supports traversal, neighbor lookup, path finding, and subgraph extraction — enabling "query relationships" without raw SQL.

CLI: `python -m cos graph {neighbors,path,subgraph,query,stats}`

Outputs: Graph query results from existing `entities` + `entity_relations` tables (no new DB tables)

## Logic
1. `KnowledgeGraph` class wraps entities + entity_relations tables with graph semantics
2. `neighbors(entity_name)` — find all entities connected by a relation (1-hop, bidirectional)
3. `path(source, target, max_depth)` — BFS shortest path between two entities
4. `subgraph(entity_name, depth)` — extract N-hop neighborhood as nodes + edges via BFS
5. `query(entity_type, relation_type, target)` — flexible filter-based graph query with optional entity join
6. `connected_components()` — BFS-based connected component detection
7. `stats()` — node count, edge count, avg degree, component count, largest component size
8. `_build_adjacency()` — internal helper that builds bidirectional adjacency list from relations table

## Key Concepts
- **No new DB tables**: queries existing `entities` + `entity_relations` tables
- **Graph semantics over relational data**: entities are nodes, relations are edges
- **BFS traversal**: path finding and subgraph extraction use breadth-first search with depth limits
- **Bidirectional edges**: treats relations as undirected for traversal
- **Subgraph extraction**: returns dict with nodes[] and edges[] — ready for Phase 140 (visualization)
- **Edge deduplication**: subgraph uses (min, max, rel_type) key to avoid duplicate edges
- **Conditional JOIN**: query() only joins entities table when entity_type filter is specified

## Verification Checklist
- [x] `neighbors("benz_001_F")` returns 2 neighbors (scaffold + activity)
- [x] `path("benz_001_F", "benz")` finds 1-hop compound → scaffold path
- [x] `subgraph("benz", depth=1)` returns 12 nodes, 11 edges (scaffold + all compounds)
- [x] `query(relation_type="belongs_to_scaffold")` returns all 44 scaffold memberships
- [x] `connected_components()` returns 1 component with 80 nodes
- [x] `stats()` shows 44 nodes, 82 edges, 3.73 avg degree, 1 component
- [x] CLI: graph neighbors/path/subgraph/query/stats all work

## Deviations from Plan
- Fixed query() SQL aliasing bug: when entity_type is None, conditions must not use `r.` prefix since the non-join query has no table alias

## Risks (resolved)
- Performance on large graphs: BFS with depth limit mitigates — tested at 80-node/82-edge scale
- SQL aliasing: fixed conditional prefix for join vs non-join queries
- No graph-specific indexes needed at current scale (44 entities, 82 relations)

## Results
| Metric | Value |
|--------|-------|
| Graph nodes | 44 (entities) |
| Graph edges | 82 (relations) |
| Avg degree | 3.73 |
| Components | 1 (fully connected) |
| Largest component | 80 nodes |
| New DB tables | 0 (queries existing tables) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The entire CETP compound dataset forms a single connected component via scaffold membership relations. The graph layer makes multi-hop traversal trivial — `subgraph("benz", 1)` instantly returns the scaffold's 12-compound family with all activity relations, which would be a complex multi-table SQL query otherwise.
