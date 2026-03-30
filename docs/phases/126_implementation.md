# Phase 126 — Episodic Memory Layer (Runs + Outputs)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Build an episodic memory layer that records what COS has done — every pipeline run, query, and analysis becomes a retrievable episode. Episodic memory answers "what happened?" while semantic memory (Phase 127) answers "what do we know?"

CLI: `python -m cos episodes list [--investigation <id>]` / `python -m cos episodes record <description>`

Outputs: Episode records in SQLite `episodes` table

## Logic
1. Create `cos/memory/episodic.py` with `EpisodicMemory` class
2. `episodes` table: id, episode_type, description, input_summary, output_summary, investigation_id, duration_s, cost_usd, created_at
3. Episode types: `ingestion`, `extraction`, `embedding`, `search`, `pipeline`, `analysis`, `manual`
4. `record(type, description, input_summary, output_summary, investigation_id, duration, cost)` — log an episode
5. `recall(investigation_id, episode_type, limit)` — retrieve past episodes
6. Integration: pipeline runs (Phase 114) auto-record episodes via event bus (Phase 116)
7. `get_recent(limit)` — most recent episodes across all investigations

## Key Concepts
- **Episodic memory**: "what happened" — records of actions taken, not facts learned
- **MemoryItem kind = episodic** (from Architect Notes schema)
- **Auto-recording**: future phases emit events → episodic memory listens and records
- **Cost tracking integration**: each episode can include its cost (from Phase 104)
- **Searchable by type + investigation**: filter by what kind of work was done

## Verification Checklist
- [ ] `record()` creates episode with all fields
- [ ] `recall(investigation_id)` returns episodes for that investigation
- [ ] `recall(episode_type="ingestion")` filters by type
- [ ] `get_recent(5)` returns last 5 episodes across all
- [ ] CLI: episodes list + episodes record work

## Risks
- Episode volume: every action creates an episode — may need pruning at scale
- Auto-recording not implemented in v0 — manual record() calls for now
- Cost field may be 0 for free operations — that's fine, tracks non-API work too
