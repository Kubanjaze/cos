# Phase 118 — Cache Layer (Prompt + Retrieval Caching)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
SQLite-backed caching with TTL expiration and hit counting. Reduces cost by avoiding redundant API calls and computations.

CLI: `python -m cos cache stats` / `python -m cos cache clear`

Outputs: Cache entries in SQLite `cache` table

## Logic
1. `CacheManager` with set/get/invalidate/clear/stats
2. `cache` table: key (primary), value_json, created_at, expires_at, hit_count
3. `get()` checks expiration — removes expired entries automatically
4. `get()` increments hit_count on cache hits
5. TTL default: 3600s (1 hour), configurable per entry

## Key Concepts
- **TTL expiration**: entries auto-expire, cleaned on next access
- **Hit counting**: tracks reuse frequency per entry
- **JSON storage**: values serialized with `json.dumps(default=str)`
- **SQLite persistence**: cache survives restarts (unlike in-memory dicts)
- **ADR-005**: directly reduces cost metric by avoiding redundant API calls

## Verification Checklist
- [x] set + get: stores and retrieves value
- [x] Hit count increments on cache hits (2 after 2 gets)
- [x] Expired entry returns None (TTL=0)
- [x] invalidate removes specific entry
- [x] stats shows active entries + total hits
- [x] clear removes all entries

## Risks (resolved)
- Stale cache: TTL mitigates, callers choose appropriate TTL
- JSON serialization: `default=str` handles non-serializable types
- Cache growth: no auto-pruning beyond TTL — acceptable for v0

## Results
| Metric | Value |
|--------|-------|
| Tests | 6/6 (set, get, hit count, expired, invalidate, clear) |
| Hit count tracking | 2 hits after 2 gets |
| TTL=0 expiration | Returns None correctly |
| DB table | cache (7th table in cos.db) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: SQLite-backed caching with hit counting gives both performance (avoid re-computation) and observability (which queries are most reused). The TTL + auto-cleanup pattern keeps the cache self-managing.
