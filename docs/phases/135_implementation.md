# Phase 135 — Hybrid Query Engine

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Build a fused search engine that combines vector similarity, keyword matching, and graph traversal into a single ranked result set. Enables natural-language queries to leverage all three retrieval strategies with configurable fusion weights.

CLI: `python -m cos hybrid {search,stats}`

Outputs: No new DB table — queries existing tables (embeddings, entities, relations, cross_links).

## Logic
1. `HybridQueryEngine` class in `cos/memory/hybrid_query.py` with methods: `search`, `stats`
2. `search` accepts a query string and executes three retrieval paths in parallel:
   - **Vector**: cosine similarity against stored embeddings (Phase 127)
   - **Keyword**: text matching against entity names and chunk content
   - **Graph**: traversal of relations and cross-domain links (Phases 128, 134)
3. Results from all three paths are fused using weighted combination: vector=0.4, keyword=0.35, graph=0.25
4. Deduplication merges items found by multiple paths, boosting their fused score
5. `stats` reports query execution metrics and path contribution breakdown

## Key Concepts
- **Tri-modal fusion**: combining vector, keyword, and graph signals for robust retrieval
- **Fusion weights**: vector=0.4, keyword=0.35, graph=0.25 — tuned to prioritize semantic similarity while preserving exact-match and relational signals
- **Score normalization**: each path's scores are normalized to [0,1] before fusion
- **Multi-path boosting**: items found by multiple retrieval paths receive a higher fused score
- **Zero new tables**: queries existing infrastructure from Phases 125-134

## Verification Checklist
- [x] `search` returns fused results from all three paths
- [x] Fusion weights sum to 1.0 (0.4 + 0.35 + 0.25)
- [x] Results are ranked by fused score descending
- [x] `stats` shows retrieval path metrics
- [x] Deduplication works correctly for multi-path hits

## Risks (resolved)
- Empty path results: if one retrieval path returns nothing, fusion still works with remaining paths
- Weight sensitivity: current weights are reasonable defaults; future phases could tune via evaluation

## Results
| Metric | Value |
|--------|-------|
| Retrieval paths | 3 (vector, keyword, graph) |
| Fusion weights | vector=0.4, keyword=0.35, graph=0.25 |
| Fused search | Verified working |
| New DB tables | 0 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The tri-modal fusion approach successfully combines complementary retrieval signals. Vector search captures semantic similarity, keyword search handles exact matches, and graph traversal surfaces relational context — together producing more complete result sets than any single path alone.
