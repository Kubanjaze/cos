# Phase 128 — Procedural Memory Layer (Saved Workflows)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Store reusable procedures — step-by-step recipes for "how we do things." Completes the 3-kind memory model (episodic Phase 126 + semantic Phase 127 + procedural). Procedural memory is persistent in SQLite, user-defined at runtime, with execution feedback counters.

Key distinction from pipelines (Phase 114): pipeline registry is in-memory/code-defined. Procedural memory is persistent, user-created, with success/fail tracking.

CLI: `python -m cos procedures {define,list,get,run,update,delete,stats}`

Outputs: Procedure records in SQLite `procedures` table (table 16)

## Logic
1. `procedures` table: id, name, name_lower, description, domain, category, steps_json, steps_schema_version, source_ref, success_count, fail_count, last_run_at, last_run_status, investigation_id, created_at, updated_at
2. `define()` — validate each step's `command` exists in registry at define-time. Store with `name_lower` for uniqueness. Reject duplicate name.
3. `get()` — case-insensitive via `name_lower` column
4. `list_procedures()` — optional domain/category filters, ordered by success_count DESC
5. `run()` — execute steps sequentially via `registry.run()`. Stop on first failure. Increment success_count or fail_count in finally path. Update last_run_at + last_run_status. Return result dict.
6. `update()` — modify description/steps/domain. If steps changed, re-validate commands.
7. `delete()` — remove by name (case-insensitive)
8. `stats()` — total, by_domain, by_category, total_runs, overall success_rate

## Key Concepts
- **Procedural = "how we do things"**: reusable step sequences, not facts or action logs
- **MemoryItem kind=procedural** per Architect Notes schema
- **Steps JSON schema v1**: `[{"command": "...", "kwargs": {...}, "subcommand": "..."}]`
- **Define-time validation**: command names checked against registry before persisting
- **Execution feedback**: success_count/fail_count increment on every run
- **last_run_at + last_run_status**: lightweight run audit without full history table
- **Case-insensitive uniqueness**: name_lower column with unique index (same pattern as Phase 127)
- **steps_schema_version**: INTEGER column for forward-compat as command signatures evolve

## Verification Checklist
- [ ] Define a 3-step procedure (status → config validate → storage)
- [ ] Get by name (case-insensitive)
- [ ] Name uniqueness: defining duplicate name raises clear error
- [ ] Invalid command rejection at define-time
- [ ] Run procedure, verify success_count increments + last_run_at updates
- [ ] Run procedure with bad step, verify fail_count increments (no crash)
- [ ] List filtered by domain
- [ ] Update steps with re-validation
- [ ] Delete procedure
- [ ] Stats show totals + success_rate

## Risks
- Steps JSON with invalid commands: mitigated — validate at define-time
- Run failure mid-execution: mitigated — fail_count increments in finally path, no rollback
- name_lower uniqueness follows Phase 127 pattern (proven)
- No auto-learning yet — procedures are manually defined; auto-capture deferred to Phase 178
