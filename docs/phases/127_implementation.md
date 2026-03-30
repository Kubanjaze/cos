# Phase 127 — Semantic Memory Layer (Concept Definitions)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Store structured knowledge — concept definitions, domain facts, and learned relationships — as retrievable semantic memory. Semantic memory answers "what do we know?" vs episodic memory's "what happened?" (Phase 126). This is the MemoryItem kind=semantic per Architect Notes schema.

CLI: `python -m cos concepts {define,list,get,search,update,stats}`

Outputs: Concept records in SQLite `concepts` table (table 15)

## Logic
1. `concepts` table: id, name, definition, domain, category, confidence, source_ref, investigation_id, created_at, updated_at
2. `define()` stores a new concept with definition, domain, category, and confidence
3. `get()` retrieves a concept by name (case-insensitive lookup)
4. `search()` finds concepts by domain, category, or text substring in name/definition
5. `update()` modifies an existing concept's definition or confidence (tracks update timestamp)
6. `list_concepts()` returns all concepts with optional domain/category filters
7. `stats()` returns total counts, breakdown by domain and category

## Key Concepts
- **Semantic = "what we know"**: facts, definitions, domain knowledge — not action records
- **MemoryItem kind=semantic** per Architect Notes schema
- **Confidence scoring**: 0.0–1.0 float, reflects certainty of the knowledge
- **Source provenance**: source_ref links to artifact/document/entity that produced this knowledge
- **Domain scoping**: concepts belong to domains (e.g., cheminformatics, clinical, general)
- **Category taxonomy**: concept types (e.g., compound, target, assay, mechanism, general)
- **Case-insensitive lookup**: concept names normalized for retrieval
- **Upsert semantics**: defining an existing concept name updates it (bumps confidence if higher)

## Verification Checklist
- [ ] `define("CETP", "Cholesteryl ester transfer protein...", domain="cheminformatics")` creates concept
- [ ] `get("cetp")` returns the concept (case-insensitive)
- [ ] `search(domain="cheminformatics")` returns domain-scoped concepts
- [ ] `search(text="protein")` finds concepts by definition substring
- [ ] `update("cetp", confidence=0.95)` updates confidence + updated_at
- [ ] `list_concepts()` returns all stored concepts
- [ ] `stats()` shows total, by_domain, by_category counts
- [ ] CLI: concepts define/list/get/search/stats all work

## Risks
- Concept name collisions across domains: use (name, domain) as logical key
- Definition drift: upsert semantics may overwrite good definitions — track updated_at for audit
- Scale: no pruning yet (deferred to Phase 133)
- No embedding integration yet: text search only (semantic search via Phase 135 hybrid query)
