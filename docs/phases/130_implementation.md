# Phase 130 — Provenance Tracking (Source Traceability)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Make the implicit provenance chain explicit and queryable. Any COS output (entity, relation, concept, episode) can be traced back through the processing chain to its original source file. Addresses Architect Notes risk #5: "If sources aren't traceable, outputs won't be trusted."

CLI: `python -m cos provenance {trace,chain,lineage,register,backfill,stats}`

Outputs: Provenance records in SQLite `provenance` table (table 17)

## Logic
1. `provenance` table: id, target_type, target_id, source_type, source_id, operation, agent, investigation_id, created_at
2. `register()` — record a provenance link with unique constraint on (target, source, operation)
3. `trace(target_type, target_id)` — walk backward: find all sources for a given output
4. `chain(source_type, source_id)` — walk forward: find all outputs derived from a given source
5. `get_lineage(target_type, target_id)` — recursive trace to root, follows first source at each hop
6. `backfill()` — reconstruct provenance from existing FK links: documents→artifacts, chunks→documents, entities→chunks, relations→chunks, embeddings→chunks
7. `stats()` — total links, by operation, by target type

## Key Concepts
- **Provenance = backward traceability**: any output traces to its source
- **Lineage = recursive backward walk**: entity → chunk → document → artifact (root)
- **Chain = forward traceability**: any input traces to all derived outputs
- **Backfill reconstructs implicit chain**: reads existing FK relationships across 5 tables
- **Operation types**: ingest, chunk, extract_entity, extract_relation, embed, define_concept
- **Agent field**: records what module performed the operation
- **Unique constraint**: (target_type, target_id, source_type, source_id, operation) prevents duplicates
- **INSERT OR IGNORE**: backfill is idempotent — safe to run multiple times

## Verification Checklist
- [x] `backfill()` reconstructs 134 provenance links from existing data
- [x] `trace("entity", ent_id)` returns source chunk
- [x] `lineage("entity", ent_id)` walks 3 hops: entity → chunk → document → artifact
- [x] `chain("chunk", chunk_id)` returns 15 derived outputs (entities + relations)
- [x] `register()` creates manual provenance link (concept → entity)
- [x] `stats()` shows 134 links: 82 relations, 44 entities, 7 chunks, 1 document
- [x] CLI: provenance trace/chain/lineage/register/backfill/stats all work

## Deviations from Plan
- Added `lineage` CLI subcommand (was `get_lineage()` API-only in plan)
- Added `backfill` CLI subcommand for reconstructing provenance from existing data
- `chain()` takes (source_type, source_id) instead of just artifact_id — more general

## Risks (resolved)
- Retroactive provenance: **resolved** — backfill() reconstructs from existing FK links, idempotent
- Provenance volume: 134 links for current dataset — manageable
- Embedding provenance: handled with try/except in case table doesn't exist yet

## Results
| Metric | Value |
|--------|-------|
| Provenance links (backfill) | 134 |
| By operation | extract_relation: 82, extract_entity: 44, chunk: 7, ingest: 1 |
| By target type | relation: 82, entity: 44, chunk: 7, document: 1 |
| Max lineage depth | 3 hops (entity → chunk → document → artifact) |
| DB table | provenance (table 17) |
| DB indexes | 5 (PK + target, source, operation, investigation + unique constraint) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The backfill approach proves that provenance can be reconstructed from existing FK links — no data loss from adding provenance tracking retroactively. The 3-hop lineage (entity → chunk → document → artifact) demonstrates full traceability from any extracted entity back to its original source file, directly addressing Architect Notes risk #5.
