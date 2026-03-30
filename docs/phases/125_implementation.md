# Phase 125 — Temporal Tagging (Time-Aware Memory)

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Add temporal awareness to COS memory — tag entities, documents, and relations with time context so the system can track how knowledge evolves over time. Enables queries like "what was the most potent compound as of March 2026?"

CLI: `python -m cos temporal tag <entity_name> --time-context <context>` / `python -m cos temporal timeline <investigation_id>`

Outputs: Temporal annotations in SQLite `temporal_tags` table

## Logic
1. Create `cos/memory/temporal.py` with `TemporalTagger` class
2. `temporal_tags` table: id, target_type (entity/document/relation), target_id, time_context, time_point, time_range_start, time_range_end, created_at
3. `tag(target_type, target_id, time_context, time_point=None)` — add temporal context
4. `get_timeline(investigation_id)` — ordered events for an investigation
5. Auto-tagging: documents get ingestion timestamp, entities get extraction timestamp
6. `time_context` is free-text: "Q1 2026 assay data", "pre-clinical phase", "2026-03-27 run"

## Key Concepts
- **Time-aware memory**: knowledge changes — temporal tags capture when facts were true
- **time_context**: human-readable temporal description (free-text)
- **time_point**: optional ISO datetime for precise events
- **Timeline view**: ordered list of events for an investigation
- **Foundation for Phase 131**: temporal context needed to detect contradictions (old vs new data)

## Verification Checklist
- [ ] `tag()` creates temporal annotation on entity
- [ ] `tag()` works on documents and relations too
- [ ] `get_timeline()` returns ordered events
- [ ] CLI: temporal tag + temporal timeline work
- [ ] Auto-tagging: documents tagged with ingestion time

## Risks
- Free-text time_context is unstructured — acceptable for v0, parse in future
- Timeline ordering: uses time_point if present, falls back to created_at
- No time-range queries in v0 — linear scan of timeline
