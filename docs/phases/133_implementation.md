# Phase 133 — Memory Pruning

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Add pruning capabilities to remove expired, low-scoring, or stale memory items. Supports dry-run mode for safe previewing before destructive operations.

CLI: `python -m cos prune {episodes,cache,dry-run,stats}`

Outputs: No new DB table — operates on existing tables to remove qualifying items.

## Logic
1. `MemoryPruner` class in `cos/memory/pruning.py` with methods: `prune_episodes`, `prune_low_score`, `prune_stale_cache`, `dry_run`, `prune_stats`
2. `prune_episodes` removes episodic memory items past their TTL
3. `prune_low_score` removes items below a configurable score threshold (uses Phase 132 scores)
4. `prune_stale_cache` removes cached items that have expired
5. `dry_run` mode previews what would be pruned without deleting
6. `prune_stats` reports counts of pruneable items by category

## Key Concepts
- **Safe pruning**: dry-run mode prevents accidental data loss
- **Score-based pruning**: leverages Phase 132 composite scores for threshold-based removal
- **TTL-based expiry**: episodic and cache items have configurable time-to-live
- **No new schema**: operates entirely on existing tables (episodes, cache, memory_scores)

## Verification Checklist
- [x] `episodes` prune command runs without error
- [x] `cache` prune command runs without error
- [x] `dry-run` previews candidates without deleting
- [x] `stats` shows pruneable item counts
- [x] No data lost when nothing qualifies for pruning

## Risks (resolved)
- Accidental deletion: mitigated by dry-run mode being the safe default path
- Empty result set: 0 expired cache items is correct for a fresh system — infrastructure is ready for future use

## Results
| Metric | Value |
|--------|-------|
| Expired cache pruned | 0 (none expired) |
| Pruning infrastructure | Ready |
| New DB tables | 0 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Pruning infrastructure is in place and verified. Zero items pruned is expected for a fresh system — the value comes when the memory store grows and stale items accumulate.
