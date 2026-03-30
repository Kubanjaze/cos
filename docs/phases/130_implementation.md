# Phase 130 — Provenance Tracking (Source Traceability)

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Make the implicit provenance chain explicit and queryable. Any COS output (entity, relation, concept, episode, procedure) can be traced back through the processing chain to its original source file. Addresses Architect Notes risk #5: "If sources aren't traceable, outputs won't be trusted."

CLI: `python -m cos provenance {trace,chain,register,stats}`

Outputs: Provenance records in SQLite `provenance` table (table 17) + trace queries across existing tables

## Logic
1. `provenance` table: id, target_type, target_id, source_type, source_id, operation, agent, investigation_id, created_at
2. `register()` — record a provenance link (e.g., entity was extracted from chunk which came from document)
3. `trace(target_type, target_id)` — walk backward: find all sources for a given output
4. `chain(artifact_id)` — walk forward: find all outputs derived from a given artifact
5. `get_lineage(target_type, target_id)` — full lineage tree (recursive trace to root)
6. `stats()` — total links, by operation, by target type

## Key Concepts
- **Provenance = backward traceability**: any output traces to its source
- **Lineage = forward traceability**: any input traces to its derived outputs
- **Implicit chain already exists**: artifact → document → chunk → entity → relation
- **Explicit provenance table**: captures cross-table links with operation context
- **Operation types**: ingest, chunk, extract_entity, extract_relation, embed, define_concept
- **Agent field**: records what module performed the operation (e.g., "cos.memory.entities")

## Verification Checklist
- [ ] Register provenance link: entity → chunk → document → artifact
- [ ] `trace("entity", entity_id)` returns provenance chain
- [ ] `chain(artifact_id)` returns all derived outputs
- [ ] `get_lineage(target_type, target_id)` walks to root
- [ ] `stats()` shows totals by operation and target type
- [ ] CLI: provenance trace/chain/register/stats all work

## Risks
- Retroactive provenance for existing data: build `backfill()` to reconstruct from existing FK links
- Provenance volume: one link per processing step — manageable at current scale
