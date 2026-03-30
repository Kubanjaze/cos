# Phase 123 — Structured Entity Extraction

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Extract structured entities (compounds, targets, activities, scaffolds) from document chunks. Moves beyond raw text storage to named, typed entities that can be linked and queried. Foundation for the knowledge graph (Phase 129).

CLI: `python -m cos entities extract <doc_id>` / `python -m cos entities list`

Outputs: Entity records in SQLite `entities` table

## Logic
1. Create `cos/memory/entities.py` with `EntityExtractor` class
2. `entities` table: id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at
3. Entity types: `compound`, `target`, `scaffold`, `activity_value`, `assay`, `disease`
4. Rule-based extraction for v0:
   - Compound: match patterns like `benz_001_F`, `CHEMBL\d+`
   - Target: match "KRAS", "CETP", gene names
   - Activity: match `pIC50=\d+\.\d+`, `IC50`
   - Scaffold: match family names (benz, naph, ind, quin, pyr, bzim)
5. `extract_from_document(doc_id)` — processes all chunks, stores entities
6. `get_entities(investigation_id, entity_type)` — query entities

## Key Concepts
- **Entity = typed named value from text**: compound names, targets, activity values
- **Rule-based extraction**: regex patterns for v0 — Claude-based NER in future phases
- **Source traceability**: every entity links to its source chunk_id (provenance)
- **Confidence score**: 1.0 for rule-based matches, lower for fuzzy matches
- **Foundation for Phase 124** (relationship extraction) and **Phase 129** (knowledge graph)

## Verification Checklist
- [ ] Compound entities extracted (benz_001_F, etc.)
- [ ] Activity values extracted (pIC50 values)
- [ ] Scaffold families extracted
- [ ] Each entity links to source chunk
- [ ] `entities list` CLI shows all entities
- [ ] Entity types queryable by type filter

## Risks
- Rule-based extraction is brittle — regex won't catch everything
- Entity deduplication: same compound in multiple chunks → deduplicate by (type, name)
- Confidence scoring: all 1.0 for rule-based — differentiate when NER is added
