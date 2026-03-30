# Phase 126 — Episodic Memory Layer (Runs + Outputs)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Record what COS has done — every pipeline run, query, and analysis becomes a retrievable episode. Episodic memory answers "what happened?" vs semantic memory's "what do we know?"

CLI: `python -m cos episodes list` / `episodes record <desc>` / `episodes stats`

Outputs: Episode records in SQLite `episodes` table

## Logic
1. `episodes` table: id, episode_type, description, input/output summaries, investigation_id, duration, cost
2. Episode types: ingestion, extraction, embedding, search, pipeline, analysis, manual
3. `record()` logs an episode with context; `recall()` retrieves with filters
4. `get_recent()` returns latest across all investigations

## Key Concepts
- **Episodic = "what happened"**: action records, not knowledge facts
- **MemoryItem kind=episodic** per Architect Notes schema
- **Input/output summaries**: human-readable context for each episode
- **Cost tracking**: each episode optionally records its API cost
- **Filterable**: by investigation_id and episode_type

## Verification Checklist
- [x] `record("ingestion", ...)` creates episode with all fields
- [x] `recall("inv-cetp")` returns 3 episodes for that investigation
- [x] Episodes include input/output summaries
- [x] `stats()` shows 3 total, by type counts
- [x] CLI: episodes list, record, stats all work

## Risks (resolved)
- Episode volume at scale: pruning deferred to Phase 133 (memory pruning)
- Auto-recording via events not yet wired: manual record() for v0
- Zero-cost episodes for free ops: tracked for completeness

## Results
| Metric | Value |
|--------|-------|
| Episodes recorded | 3 (ingestion, extraction, embedding) |
| Episode types | 3 active |
| DB table | episodes (table 14) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Episodic memory is the COS audit trail — every action recorded with input/output context. Combined with temporal tags (Phase 125), we can reconstruct the full history of an investigation: what was ingested, when, what was extracted, how long it took.
