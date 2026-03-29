# Phase 119 — Rate Limit Manager

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Build a rate limit manager that enforces per-API call throttling to prevent hitting external API limits. Tracks requests per time window and sleeps when limits are approached. Integrates with Phase 111 retry system for 429 responses.

CLI: `python -m cos ratelimit stats`

Outputs: Rate limit state in `cos/core/ratelimit.py`

## Logic
1. Create `cos/core/ratelimit.py` with `RateLimiter` class
2. Token bucket algorithm: capacity + refill rate per second
3. `acquire()` — blocks until a token is available (sleeps if bucket empty)
4. `try_acquire()` — non-blocking, returns True/False
5. Per-API limits: configurable per endpoint name (e.g., "anthropic" = 5 req/s)
6. `@rate_limited(name)` decorator for automatic throttling
7. Stats: total requests, total waits, total wait time

## Key Concepts
- **Token bucket**: capacity tokens, refills at rate/sec, acquire consumes one
- **Per-API configuration**: different limits for different APIs
- **Decorator pattern**: `@rate_limited("anthropic")` wraps any function
- **Integration with retry**: 429 → TransientError → @retry with backoff
- **ADR-001**: local-first — no distributed rate limiting needed

## Verification Checklist
- [ ] Token bucket fills at configured rate
- [ ] `acquire()` blocks when bucket empty
- [ ] `try_acquire()` returns False when empty
- [ ] `@rate_limited` decorator throttles calls
- [ ] Stats track total requests + waits
- [ ] CLI shows rate limit stats

## Risks
- Sleep-based throttling blocks the thread — acceptable for sequential v0
- Clock precision on Windows — time.monotonic() is sufficient
- Multiple RateLimiter instances for same API could desync — singleton pattern handles this
