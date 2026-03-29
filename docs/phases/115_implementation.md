# Phase 115 — State Manager (Track Investigations)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Investigation lifecycle manager — the central state machine for COS's primary unit of work (ADR-003). Manages lifecycle, links artifacts/versions/costs, provides CLI for investigation management.

CLI: `python -m cos investigate create/list/show/activate/complete`

Outputs: Investigation records in SQLite `investigations` table

## Logic
1. `InvestigationManager` class with SQLite backend
2. `investigations` table: id (inv-{8hex}), title, domain, status, created_at, updated_at, tags, notes
3. Status lifecycle: created → active → completed | archived (validated transitions)
4. `create()` → `activate()` → `complete()`/`archive()` with timestamp updates
5. `get(id)` aggregates across tables: artifact count, version count, total cost
6. Human-readable IDs: `inv-396f47ac` (not full UUIDs)

## Key Concepts
- **Investigation = primary unit of work** (ADR-003): everything references investigation_id
- **State machine**: VALID_TRANSITIONS dict enforces legal status changes
- **Cross-table aggregation**: `get()` joins artifacts + versions + cost_events for full picture
- **Human-readable IDs**: `inv-{8hex}` format for CLI usability
- **Tags as CSV**: stored in investigation record for simple filtering

## Verification Checklist
- [x] `create()` returns inv-{8hex} with status=created
- [x] `activate()` transitions created → active
- [x] `list()` shows investigation with correct status
- [x] `get()` returns artifacts=0, versions=0, cost=$0.0000 (empty investigation)
- [x] CLI: create, list, show, activate all work
- [x] Invalid transitions blocked (state machine)
- [x] Sixth DB table: investigations (indexed on status)

## Risks (resolved)
- Cross-table queries: simple COUNT/SUM, fast at v0 scale
- Invalid transitions: validated via VALID_TRANSITIONS dict with ValueError
- Investigation ID collisions: 8 hex chars = 4 billion possibilities, acceptable

## Results
| Metric | Value |
|--------|-------|
| Investigation created | inv-396f47ac "What drives KRAS G12C potency?" |
| Lifecycle | created → active (validated) |
| Cross-table links | artifacts (0), versions (0), cost ($0.00) |
| DB table | investigations (indexed on status) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The Investigation as primary unit of work ties everything together. `investigate show` reveals the full picture: what was ingested, how many versions, and how much it cost — all from one command. This is the ADR-003 design coming to life.
