# Phase 119 — Rate Limit Manager

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Token bucket rate limiter for per-API call throttling. Prevents hitting external API rate limits. Configurable per-API with defaults for Anthropic, PubChem, ChEMBL.

CLI: `python -m cos ratelimit`

Outputs: `cos/core/ratelimit.py` — get_limiter(), @rate_limited, all_stats()

## Logic
1. `TokenBucket(rate, capacity)` — tokens refill at rate/sec, max capacity
2. `acquire()` — blocks until token available, returns wait time
3. `try_acquire()` — non-blocking, returns True/False
4. `get_limiter(name)` — registry of named limiters with defaults
5. `@rate_limited(name)` — decorator for automatic throttling
6. `all_stats()` — total requests, waits, wait time per limiter

## Key Concepts
- **Token bucket algorithm**: capacity tokens, refills at rate/sec, consume on acquire
- **Per-API defaults**: anthropic=5/s, pubchem=4/s, chembl=10/s
- **Global registry**: `_limiters` dict stores named limiters as singletons
- **time.monotonic()**: clock-independent timing, handles system clock changes
- **Stats tracking**: requests, waits, cumulative wait time per limiter

## Verification Checklist
- [x] 3 acquires consume 3 tokens with 0 wait (bucket starts full)
- [x] try_acquire returns False when bucket empty
- [x] After 0.15s sleep, try_acquire succeeds (tokens refilled)
- [x] @rate_limited decorator works on function
- [x] all_stats() shows per-limiter metrics

## Risks (resolved)
- Thread blocking: sleep-based — acceptable for sequential v0 (ADR-001)
- Clock precision: time.monotonic() sufficient on Windows
- Multiple limiters per API: singleton registry prevents this

## Results
| Metric | Value |
|--------|-------|
| Tests | 5/5 (acquire, try_acquire, refill, decorator, stats) |
| Default APIs | 3 (anthropic, pubchem, chembl) |
| Token bucket verified | capacity drains, refills after wait |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Token bucket is the right algorithm for API rate limiting — it naturally handles bursts (use capacity tokens immediately) then throttles to sustained rate. The per-API registry means different APIs get different limits without code changes.
