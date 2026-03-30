# Phase 132 — Memory Scoring

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Implement composite memory scoring so the system can rank memory items by importance. Each item receives a weighted score combining relevance, confidence, recency, and access frequency, enabling prioritized retrieval and pruning decisions.

CLI: `python -m cos scores {score-all,top,stats}`

Outputs: `memory_scores` table (DB table 19) populated with composite scores for all memory items.

## Logic
1. `MemoryScorer` class in `cos/memory/scoring.py` with four public methods: `score_all`, `get_top`, `record_access`, `stats`
2. `score_all` iterates over all memory items (entities + concepts) and computes a composite score per item
3. Composite formula: `relevance * 0.3 + confidence * 0.3 + recency * 0.2 + frequency * 0.2`
4. Recency decays over time; frequency increments on each access via `record_access`
5. `get_top(n)` returns the highest-scored items for prioritized retrieval
6. `stats` provides aggregate statistics (count, average, min, max)
7. Scores stored in `memory_scores` table (DB table 19) with item_id, score, component breakdown, timestamp

## Key Concepts
- **Composite scoring**: weighted sum of four orthogonal signals (relevance, confidence, recency, frequency)
- **Weight tuning**: 0.3/0.3/0.2/0.2 balances content quality (60%) vs usage patterns (40%)
- **Recency decay**: time-based decay ensures stale items lose priority over time
- **Access tracking**: `record_access` updates frequency counter for retrieval-based boosting
- **DB table 19**: `memory_scores` — persistent score storage for cross-session ranking

## Verification Checklist
- [x] `score-all` computes scores for all memory items
- [x] `top` returns items sorted by composite score descending
- [x] `stats` shows count, average, min, max scores
- [x] `record_access` increments frequency for a given item
- [x] Composite weights sum to 1.0
- [x] DB table `memory_scores` created and populated

## Risks (resolved)
- Score staleness: recency component ensures scores degrade naturally; `score-all` can be re-run to refresh
- Weight sensitivity: current 0.3/0.3/0.2/0.2 split is configurable but not yet exposed via CLI

## Results
| Metric | Value |
|--------|-------|
| Items scored | 49 (44 entities, 5 concepts) |
| Average score | 0.7875 |
| DB table | memory_scores (table 19) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The composite scoring formula produces well-distributed scores across memory items, with the 0.3/0.3/0.2/0.2 weighting providing a balanced mix of content quality and usage signals that will drive pruning (Phase 133) and prioritized retrieval.
