# Phase 115 — State Manager (Track Investigations)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build the Investigation lifecycle manager — the central state machine for COS's primary unit of work (ADR-003). An Investigation represents a question being explored: it has a lifecycle (created → active → completed/archived), links to artifacts, versions, and cost events.

CLI: `python -m cos investigate create "What drives KRAS potency?"` / `investigate list` / `investigate show <id>`

Outputs: Investigation records in SQLite `investigations` table

## Logic
1. Create `cos/core/investigations.py` with `InvestigationManager` class
2. SQLite table: `investigations(id, title, domain, status, created_at, updated_at, tags, notes)`
3. Status lifecycle: `created` → `active` → `completed` | `archived`
4. `create(title, domain, tags)` — creates investigation, returns ID
5. `activate(id)` / `complete(id)` / `archive(id)` — status transitions
6. `get(id)` — returns full investigation with linked artifacts, versions, costs
7. `list(status_filter)` — list investigations by status
8. Links to existing tables: artifacts (by investigation_id), versions, cost_events
9. CLI: `investigate create`, `investigate list`, `investigate show <id>`

## Key Concepts
- **Investigation schema** (from Architect Notes): id, question/title, domain, tags, inputs[], outputs[], created_at, updated_at, status
- **ADR-003 compliance**: Investigation is THE canonical object — everything references investigation_id
- **Cross-table aggregation**: `show` command pulls artifacts, versions, and cost from existing tables
- **Status lifecycle**: created → active → completed/archived (state machine)
- **Tags as comma-separated**: stored in investigation record, queryable

## Verification Checklist
- [ ] `create()` returns investigation with status=created
- [ ] `activate()` transitions to active
- [ ] `complete()` transitions to completed
- [ ] `get()` returns investigation with linked artifact count + total cost
- [ ] `list()` shows all investigations
- [ ] `investigate show` CLI shows full detail
- [ ] Cross-table links work (artifacts, versions, cost_events by investigation_id)

## Risks
- Cross-table queries may be slow with many records — acceptable for v0 scale
- Status transition validation: prevent invalid transitions (e.g., archived → active)
- Investigation ID format: use short human-readable IDs, not UUIDs
