# Phase 128 — Procedural Memory Layer (Saved Workflows)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Store reusable procedures — step-by-step recipes for "how we do things." Completes the 3-kind memory model (episodic Phase 126 + semantic Phase 127 + procedural). Procedural memory is persistent in SQLite, user-defined at runtime, with execution feedback counters.

Key distinction from pipelines (Phase 114): pipeline registry is in-memory/code-defined. Procedural memory is persistent, user-created, with success/fail tracking.

CLI: `python -m cos procedures {define,list,get,run,update,delete,stats}`

Outputs: Procedure records in SQLite `procedures` table (table 16)

## Logic
1. `procedures` table: id, name, name_lower, description, domain, category, steps_json, steps_schema_version, source_ref, success_count, fail_count, last_run_at, last_run_status, investigation_id, created_at, updated_at (16 columns)
2. `define()` — validate each step's `command` (and `subcommand` if present) against registry at define-time. Store with `name_lower` for uniqueness. Reject duplicate name with clear error message.
3. `get()` — case-insensitive via `name_lower` column
4. `list_procedures()` — optional domain/category filters, ordered by success_count DESC
5. `run()` — execute steps sequentially via `registry.run()`. Detects registry error strings (`"Error: ..."` pattern). Stop on first failure. Increment success_count or fail_count in `finally` path. Update last_run_at + last_run_status.
6. `update()` — modify description/steps/domain/category. If steps changed, re-validate commands.
7. `delete()` — remove by name (case-insensitive)
8. `stats()` — total, total_runs, success/fail counts, success_rate, by_domain, by_category

## Key Concepts
- **Procedural = "how we do things"**: reusable step sequences, not facts or action logs
- **MemoryItem kind=procedural** per Architect Notes schema — completes 3-kind model
- **Steps JSON schema v1**: `[{"command": "...", "kwargs": {...}, "subcommand": "..."}]`
- **Define-time validation**: command AND subcommand names checked against registry before persisting
- **Registry error detection**: `run()` checks for `"Error: ..."` return strings from registry (which swallows exceptions)
- **Execution feedback**: success_count/fail_count increment in `finally` path — guaranteed even on exceptions
- **last_run_at + last_run_status**: lightweight run audit without full history table
- **Case-insensitive uniqueness**: name_lower column with unique index (same pattern as Phase 127)
- **steps_schema_version**: INTEGER column for forward-compat as command signatures evolve
- **Duplicate rejection**: clear error message directing user to `update()` instead

## Verification Checklist
- [x] Define a 3-step procedure (status → config validate → storage)
- [x] Get by name (case-insensitive: "system health check" matches "System Health Check")
- [x] Name uniqueness: defining duplicate name raises clear error with existing ID
- [x] Invalid command rejection: `{"command": "does_not_exist"}` fails at define-time
- [x] Run procedure, verify success_count increments + last_run_at updates
- [x] Run procedure with bad step (nonexistent file ingest), verify fail_count increments (no crash)
- [x] List filtered by domain
- [x] Update procedure description
- [x] Delete procedure
- [x] Stats show totals + success_rate

## Deviations from Plan
- Added registry error detection: `registry.run()` swallows exceptions and returns `"Error: ..."` strings (Phase 110 design). Added check in `run()` to detect these and treat as failures. Without this, all steps would appear to succeed.
- Subcommand validation added to `_validate_steps()` — not just command but also subcommand checked against registry.

## Risks (resolved)
- Steps JSON with invalid commands: **mitigated** — validate at define-time (command + subcommand)
- Run failure mid-execution: **mitigated** — fail_count increments in finally path, no rollback
- Registry swallowing errors: **mitigated** — detect "Error: ..." pattern in run output
- name_lower uniqueness follows Phase 127 pattern (proven)
- No auto-learning yet — procedures are manually defined; auto-capture deferred to Phase 178

## Results
| Metric | Value |
|--------|-------|
| Procedures defined | 2 (System Health Check + Fail Test) |
| Procedures after cleanup | 1 (Fail Test deleted during verification) |
| Successful runs | 1 (3-step health check: 0.008s) |
| Failed runs | 1 (step 2 ingest nonexistent file) |
| DB table | procedures (table 16) |
| DB indexes | 5 (PK + unique name_lower, domain, category, inv) |
| Columns | 16 (incl. steps_schema_version, success/fail counters, last_run audit) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Procedural memory completes the 3-kind memory model from the Architect Notes (episodic/semantic/procedural). The define-time validation catches errors early, and the registry error detection ensures accurate success/fail tracking despite the registry's exception-swallowing design. Success rate tracking per procedure creates a natural quality signal for future phases (Phase 178 auto-learning, Phase 132 memory scoring).
