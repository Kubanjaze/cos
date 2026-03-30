# Phase 125 — Temporal Tagging (Time-Aware Memory)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Add temporal awareness to COS memory. Entities, documents, and relations can be annotated with time context. Enables timeline views of investigation progress.

CLI: `python -m cos temporal tag <type> <id> --context <text>` / `python -m cos temporal timeline <inv_id>`

Outputs: Temporal annotations in SQLite `temporal_tags` table

## Logic
1. `temporal_tags` table: target_type, target_id, time_context (free-text), time_point (optional ISO)
2. `tag()` creates annotation on any target (entity, document, relation)
3. `get_timeline()` returns ordered events — sorts by time_point, falls back to created_at
4. `get_tags()` returns all temporal tags for a specific target

## Key Concepts
- **Time-aware memory**: facts change over time — temporal tags capture when
- **time_context**: human-readable description ("Q1 2026 assay data")
- **time_point**: optional ISO datetime for precise ordering
- **Timeline ordering**: COALESCE(time_point, created_at) for mixed-precision events
- **Foundation for Phase 131**: temporal context needed for contradiction detection

## Verification Checklist
- [x] `tag("entity", "benz_001_F", "Initial library screening")` creates annotation
- [x] `tag("document", "doc-4c1efa86", ..., time_point="2026-03-27T16:55:00")` with precise time
- [x] `get_timeline("inv-cetp")` returns 3 events in chronological order
- [x] Timeline orders by time_point when present, created_at when not
- [x] CLI: temporal tag + temporal timeline work

## Risks (resolved)
- Free-text time_context: unstructured but human-readable — parse in future
- Timeline ordering: COALESCE handles mixed time_point/created_at correctly
- No time-range queries: linear scan acceptable for v0 scale

## Results
| Metric | Value |
|--------|-------|
| Tags created | 3 (2 entities + 1 document) |
| Timeline | 3 events, chronologically ordered |
| DB table | temporal_tags (table 13) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The COALESCE ordering correctly interleaves precise time_points (2026-03-27, 2026-03-29) with fallback created_at timestamps. This enables a unified timeline regardless of whether events have precise timestamps or not.
