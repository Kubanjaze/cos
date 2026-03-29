# Phase 120 — System Health Dashboard (Internal)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build a system health dashboard that aggregates status from all COS core modules into a single view. Shows storage usage, cache stats, cost totals, task queue status, investigation counts, rate limiter state, and recent events. The "cockpit view" of COS.

CLI: `python -m cos health`

Outputs: Aggregated health report printed to console

## Logic
1. Create `cos/core/health.py` with `get_health_report()` function
2. Aggregate from all core modules:
   - Storage: file count + size, DB size + table count (Phase 108)
   - Cache: active entries + hit rate (Phase 118)
   - Cost: total spend, per-model breakdown (Phase 104)
   - Tasks: pending/running/completed/failed counts (Phase 107)
   - Investigations: count by status (Phase 115)
   - Rate limiters: active limiters + wait stats (Phase 119)
3. Return structured dict, render as formatted console output
4. CLI: `health` command — single comprehensive status view

## Key Concepts
- **Aggregation module**: pulls from all other core modules without adding logic
- **Cockpit view**: one command to see everything — the "top" of COS
- **Zero new tables**: purely reads from existing modules
- **Track A capstone**: this phase ties together all 19 prior Track A modules
- **ADR-005 eval preview**: health report includes quality/cost/latency seed metrics

## Verification Checklist
- [ ] Storage stats present (file count, DB size, tables)
- [ ] Cache stats present (entries, hits)
- [ ] Cost total present
- [ ] Task counts present
- [ ] Investigation counts present
- [ ] Rate limiter stats present
- [ ] `python -m cos health` renders clean formatted output
- [ ] Track A complete: all 20 phases built and verified

## Risks
- Module import errors: wrap each section in try/except — partial report is better than crash
- Performance: all queries are simple aggregations, fast at v0 scale
- Data consistency: point-in-time snapshot, not transactional — acceptable
