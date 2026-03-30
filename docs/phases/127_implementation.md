# Phase 127 — Semantic Memory Layer (Concept Definitions)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Store structured knowledge — concept definitions, domain facts, and learned relationships — as retrievable semantic memory. Semantic memory answers "what do we know?" vs episodic memory's "what happened?" (Phase 126). This is the MemoryItem kind=semantic per Architect Notes schema.

CLI: `python -m cos concepts {define,list,get,search,update,stats}`

Outputs: Concept records in SQLite `concepts` table (table 15)

## Logic
1. `concepts` table: id, name, name_lower, definition, domain, category, confidence, source_ref, investigation_id, created_at, updated_at
2. `name_lower` stored for case-insensitive lookups; unique index on (name_lower, domain)
3. `define()` stores a new concept or upserts an existing one (same name+domain = update, confidence takes max)
4. `get()` retrieves by name (case-insensitive), returns highest-confidence match if no domain specified
5. `search()` finds by domain, category, or text substring in name/definition (LIKE queries)
6. `update()` modifies specific fields of an existing concept (definition, category, confidence, source_ref)
7. `list_concepts()` returns all concepts with optional domain/category filters, ordered by confidence DESC
8. `stats()` returns total, avg_confidence, breakdown by domain and category

## Key Concepts
- **Semantic = "what we know"**: facts, definitions, domain knowledge — not action records
- **MemoryItem kind=semantic** per Architect Notes schema
- **Confidence scoring**: 0.0–1.0 float, reflects certainty of the knowledge
- **Source provenance**: source_ref links to artifact/document/entity that produced this knowledge
- **Domain scoping**: concepts belong to domains (e.g., cheminformatics, clinical, general)
- **Category taxonomy**: concept types (e.g., compound, target, assay, method, metric, general)
- **Case-insensitive lookup**: name_lower column with index for efficient retrieval
- **Upsert semantics**: define() with existing name+domain updates (bumps confidence to max of old/new)
- **Unique constraint**: (name_lower, domain) prevents duplicates

## Verification Checklist
- [x] `define("CETP", "Cholesteryl ester transfer protein...", domain="cheminformatics")` creates concept
- [x] `get("cetp")` returns the concept (case-insensitive)
- [x] `search(domain="cheminformatics")` returns domain-scoped concepts
- [x] `search(text="protein")` finds concepts by definition substring
- [x] `update("cetp", confidence=0.95)` updates confidence + updated_at
- [x] Upsert: re-defining same name+domain updates instead of duplicating
- [x] `list_concepts()` returns all stored concepts ordered by confidence
- [x] `stats()` shows total, avg_confidence, by_domain, by_category counts
- [x] CLI: concepts define/list/get/search/update/stats all work

## Risks (resolved)
- Concept name collisions across domains: resolved with unique (name_lower, domain) index
- Definition drift: upsert tracks updated_at for audit trail; confidence takes max to avoid downgrading
- Scale: no pruning yet (deferred to Phase 133)
- No embedding integration yet: text search only (semantic search via Phase 135 hybrid query)
- Category changed on upsert: noted — upsert updates category to latest value (intentional, not a bug)

## Results
| Metric | Value |
|--------|-------|
| Concepts defined | 4 (CETP, IC50, Morgan Fingerprint, Scaffold Split) |
| Domains | 1 (cheminformatics) |
| Categories | 3 (target, metric, method) |
| Avg confidence | 0.920 |
| DB table | concepts (table 15) |
| DB indexes | 5 (PK + name, domain, category, inv, unique name+domain) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Semantic memory completes the three-kind memory model (episodic/semantic/procedural per Architect Notes). Upsert semantics with max-confidence prevent knowledge degradation while allowing definitions to evolve. The (name_lower, domain) unique constraint naturally supports multi-domain concept stores without collision.
