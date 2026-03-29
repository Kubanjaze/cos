# Phase 118 — Cache Layer (Prompt + Retrieval Caching)

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Build a caching layer that stores expensive computation results (API responses, embeddings, query results) with TTL-based expiration. Reduces cost (ADR-005: 40% weight) by avoiding redundant API calls.

CLI: `python -m cos cache stats` / `python -m cos cache clear`

Outputs: Cache entries in SQLite `cache` table

## Logic
1. Create `cos/core/cache.py` with `CacheManager` class
2. SQLite table: `cache(key, value_json, created_at, expires_at, hit_count)`
3. `get(key)` — returns cached value if not expired, else None (cache miss)
4. `set(key, value, ttl_seconds=3600)` — stores value with expiration
5. `invalidate(key)` — remove specific entry
6. `clear()` — remove all entries
7. `stats()` — total entries, total hits, expired count, size
8. Auto-cleanup: expired entries removed on `get()` calls

## Key Concepts
- **Content-based keys**: hash of (operation + input) for deterministic cache keys
- **TTL expiration**: default 1 hour, configurable per entry
- **Hit counting**: tracks how often each cache entry is reused
- **SQLite persistence**: cache survives process restarts (unlike in-memory)
- **ADR-005 cost reduction**: caching API responses directly reduces cost metric

## Verification Checklist
- [ ] `set("key", {"data": 1})` stores entry
- [ ] `get("key")` returns cached value
- [ ] `get("key")` after TTL returns None (expired)
- [ ] `stats()` shows total entries + hits
- [ ] `clear()` removes all entries
- [ ] Hit count increments on cache hits

## Risks
- Stale cache: TTL mitigates, but callers must choose appropriate TTL
- Cache size growth: no automatic pruning beyond TTL — add LRU in future
- JSON serialization: values must be JSON-serializable
