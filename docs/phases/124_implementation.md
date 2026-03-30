# Phase 124 — Relationship Extractor (Entity Links)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Extract relationships between entities (e.g., "benz_001_F has_activity pIC50=7.25", "benz_001_F belongs_to benz scaffold"). Builds typed edges between Phase 123 entities — the foundation for the knowledge graph.

CLI: `python -m cos relations extract <doc_id>` / `python -m cos relations list`

Outputs: Relationship records in SQLite `entity_relations` table

## Logic
1. Create `cos/memory/relations.py` with `RelationExtractor` class
2. `entity_relations` table: id, source_entity_id, relation_type, target_entity_id, target_value, confidence, source_chunk_id, document_id, created_at
3. Relation types: `has_activity`, `belongs_to_scaffold`, `targets`, `measured_in`
4. Rule-based extraction for v0:
   - Co-occurrence in same chunk: compound + pIC50 value → `has_activity`
   - Name prefix: compound name prefix → scaffold family → `belongs_to_scaffold`
5. `extract_from_document(doc_id)` — processes entities from Phase 123, infers relations
6. `get_relations(entity_name)` — find all relations for an entity

## Key Concepts
- **Relation = typed edge between entities**: source → relation_type → target
- **Co-occurrence heuristic**: entities in same chunk are likely related
- **Name-based inference**: compound prefix determines scaffold membership
- **Provenance**: relations linked to source chunk for traceability
- **Foundation for Phase 129**: relations become edges in the knowledge graph

## Verification Checklist
- [ ] `has_activity` relations created (compound → pIC50)
- [ ] `belongs_to_scaffold` relations created (compound → scaffold)
- [ ] Relations linked to source chunks
- [ ] `get_relations("benz_001_F")` returns activity + scaffold relations
- [ ] CLI: relations extract, list work

## Risks
- Co-occurrence is noisy — compounds may co-occur with wrong pIC50 values in same chunk
- Name-based scaffold inference only works for our naming convention
- Relation deduplication needed via UNIQUE constraint
