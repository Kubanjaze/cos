# Phase 111 — Error Handling + Retry System

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Centralized error handling and retry system. Provides error hierarchy, @retry decorator with exponential backoff, and safe_execute wrapper. All COS modules use this instead of ad-hoc try/except.

CLI: Self-test via Python (no CLI subcommand — utility module)

Outputs: `cos/core/errors.py` — importable error handling utilities

## Logic
1. Error hierarchy: `COSError` → `TransientError` (retryable) / `PermanentError` (fail fast)
2. Subclasses: `RateLimitError(TransientError)`, `ValidationError(PermanentError)`
3. `@retry(max_attempts, backoff_base, max_delay, retryable)` decorator
4. Backoff: `min(backoff_base * 2^attempt, max_delay)` with structured logging per attempt
5. `safe_execute(fn, default=None)` — catch-all wrapper
6. `classify_http_error(status_code)` — maps HTTP codes to error types

## Key Concepts
- **Error hierarchy**: TransientError retried, PermanentError fails immediately
- **@retry decorator**: exponential backoff, configurable max_attempts/backoff_base
- **Backoff cap**: 60s default, prevents infinite waits
- **classify_http_error**: 429→RateLimitError, 500/502/503→TransientError, 400/401/404→PermanentError
- **safe_execute**: returns default on any exception — for non-critical operations
- **Structured logging**: retry attempts logged with count + delay

## Verification Checklist
- [x] @retry retries TransientError up to max_attempts (3 attempts, succeeded on 3rd)
- [x] @retry does NOT retry PermanentError (failed after 1 attempt)
- [x] Exponential backoff: 0.05s → 0.10s delays verified
- [x] safe_execute returns "fallback" on ValueError
- [x] classify_http_error: 429→RateLimitError, 404→PermanentError
- [x] Structured error logging includes attempt count

## Risks (resolved)
- Retry on non-idempotent ops: caller's responsibility — documented in docstring
- Backoff cap: 60s default is configurable per-call via max_delay param
- PermanentError must not be in retryable tuple: verified — @retry only catches TransientError by default

## Results
| Metric | Value |
|--------|-------|
| Error classes | 5 (COSError, TransientError, PermanentError, RateLimitError, ValidationError) |
| Tests passed | 5/5 (retry success, retry exhausted, permanent fail-fast, safe_execute, HTTP mapping) |
| External deps | 0 (stdlib only) |
| Cost | $0.00 |

Key finding: The decorator pattern keeps retry logic out of business code. `@retry(max_attempts=3)` on any function adds resilience without cluttering the function body. PermanentError correctly bypasses retry — preventing wasted attempts on auth failures or invalid input.
