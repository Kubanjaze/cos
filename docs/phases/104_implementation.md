# Phase 104 — Token + Cost Tracking Middleware (Global)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-27

## Goal
Build a global cost tracking middleware that records every API call's token usage and cost in SQLite. Answers "Where is money actually going?" per investigation, per model.

CLI: `python -m cos cost summary` / `python -m cos cost reset`

Outputs: Cost records in `~/.cos/cos.db` table `cost_events`, queryable via CLI

## Logic
1. `CostTracker` class with SQLite backend in `cos/core/cost.py`
2. `cost_events` table: id, timestamp, investigation_id, model, input_tokens, output_tokens, cost_usd, operation
3. `record()` computes cost from pricing lookup, inserts row, logs with structured fields
4. `get_total(investigation_id)` and `get_summary()` for queries
5. Budget warning: logs WARNING when investigation exceeds threshold × budget
6. CLI: `cost summary` (total + per-model + per-investigation) and `cost reset`
7. Singleton: `from cos.core.cost import cost_tracker`

## Key Concepts
- **MODEL_PRICING dict**: Haiku ($0.80/$4.00), Sonnet ($3/$15), Opus ($15/$75) per MTok
- **SQLite persistence**: cost events survive sessions, queryable with SQL (ADR-002)
- **Investigation-scoped**: every event tied to investigation_id (ADR-003)
- **Budget warnings**: threshold from settings, emitted as structured log WARNING (Phase 103 integration)
- **Singleton pattern**: `cost_tracker = CostTracker()` at module level, imported everywhere

## Verification Checklist
- [x] SQLite table created on first use
- [x] `record()` inserts with correct computed USD (Haiku: $0.0008 for 500in+100out)
- [x] `get_total("inv-001")` returns $0.0018 (sum of 2 calls)
- [x] `get_summary()` shows per-model and per-investigation breakdowns
- [x] Structured log output includes cost and investigation_id
- [x] `python -m cos cost summary` CLI works

## Risks (resolved)
- SQLite concurrent writes: not an issue for local-first single-user (ADR-001)
- Pricing may go stale: MODEL_PRICING dict is easy to update in code
- Budget warning fires on every record() after threshold — acceptable for awareness

## Results
| Metric | Value |
|--------|-------|
| Test: 3 simulated calls | Haiku×2 + Sonnet×1 |
| inv-001 total | $0.0018 (2 Haiku calls) |
| inv-002 total | $0.0105 (1 Sonnet call) |
| Grand total | $0.0123 |
| CLI output | per-model + per-investigation breakdown |
| External deps | 0 (sqlite3 is stdlib) |

Key finding: The per-investigation cost breakdown immediately shows that one Sonnet call costs 6× two Haiku calls — exactly the kind of visibility needed for ADR-005's cost optimization metric (40% eval weight).
