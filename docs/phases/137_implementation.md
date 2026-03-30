# Phase 137 — Incremental Memory Updates

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Track granular changes to the memory system so updates can be replayed, audited, or selectively applied. Every modification to memory is recorded as a change event with before/after state.

CLI: `python -m cos changes {pending,apply,stats}`

Outputs: `memory_changes` table (DB table 22) recording change events.

## Logic
1. `IncrementalUpdateTracker` class in `cos/memory/incremental.py` with methods: `record_change`, `get_pending`, `mark_applied`, `apply_pending`, `stats`
2. `record_change` logs a modification event with item_id, change_type (insert/update/delete), before/after state
3. `get_pending` retrieves changes that have not yet been applied (useful for batch processing)
4. `mark_applied` marks a specific change as applied
5. `apply_pending` processes all pending changes in order
6. `stats` reports change counts by type and status (pending vs applied)
7. Changes stored in `memory_changes` table (DB table 22) with id, item_id, change_type, before_state, after_state, status, created_at

## Key Concepts
- **Change event logging**: every memory modification produces an auditable change record
- **Pending/applied status**: changes can be queued and batch-applied, enabling review-before-commit workflows
- **Replay capability**: change log enables reconstruction of memory state at any point
- **DB table 22**: `memory_changes` — append-only change log for audit and replay

## Verification Checklist
- [x] `pending` shows unprocessed changes
- [x] `apply` processes pending changes
- [x] `stats` reports change counts by type and status
- [x] DB table `memory_changes` created
- [x] Change tracking infrastructure operational

## Risks (resolved)
- Change log growth: append-only table will grow unbounded — future phases could add archival/compaction
- Ordering: changes must be applied in sequence to maintain consistency — `apply_pending` respects insertion order

## Results
| Metric | Value |
|--------|-------|
| Change tracking | Infrastructure ready |
| DB table | memory_changes (table 22) |
| Change types supported | insert, update, delete |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The incremental update tracker provides a change-event foundation for memory system auditing. Combined with snapshots (Phase 136), this enables both point-in-time state capture and granular change replay.
