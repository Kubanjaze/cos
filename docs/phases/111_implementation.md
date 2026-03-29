# Phase 111 — Error Handling + Retry System

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Build a centralized error handling and retry system for COS. Provides decorators for automatic retry with exponential backoff, structured error logging, and error categorization (transient vs permanent). All COS modules use this instead of ad-hoc try/except.

CLI: `python -m cos test-retry` (demo/self-test)

Outputs: Error handling utilities in `cos/core/errors.py`

## Logic
1. Define error hierarchy: `COSError` base → `TransientError` (retryable) → `PermanentError` (not retryable)
2. `@retry(max_attempts, backoff_base, retryable_exceptions)` decorator
3. Exponential backoff: wait = backoff_base * 2^attempt (capped at 60s)
4. Structured error logging: error type, attempt count, delay, original exception
5. `safe_execute(fn, *args, default=None)` — run function, return default on failure
6. All errors logged with investigation_id context when available

## Key Concepts
- **Error hierarchy**: COSError → TransientError (retry) vs PermanentError (fail fast)
- **@retry decorator**: exponential backoff with configurable max_attempts and retryable types
- **Backoff formula**: `min(backoff_base * 2^attempt, 60)` seconds
- **safe_execute**: catch-all wrapper returning default on any failure
- **Structured logging integration**: errors logged with Phase 103 structured fields
- **API error mapping**: HTTP 429/500/502/503 → TransientError; 400/401/404 → PermanentError

## Verification Checklist
- [ ] `@retry` retries TransientError up to max_attempts
- [ ] `@retry` does NOT retry PermanentError
- [ ] Exponential backoff delays verified (0.1s → 0.2s → 0.4s...)
- [ ] `safe_execute` returns default on failure
- [ ] Error hierarchy: isinstance checks work correctly
- [ ] Structured error logging includes attempt count

## Risks
- Retry on non-idempotent operations could cause duplicates — caller must ensure idempotency
- Backoff cap at 60s may be too short for rate-limited APIs — configurable per call
- Thread safety of retry state: not an issue for local-first sequential execution (ADR-001)
