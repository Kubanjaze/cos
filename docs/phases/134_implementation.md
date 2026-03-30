# Phase 134 — Cross-Domain Linking

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Enable discovery and management of links between memory items that span different knowledge domains. Cross-domain links connect concepts that appear in multiple contexts (e.g., a drug target studied in both cheminformatics and clinical domains).

CLI: `python -m cos crosslinks {discover,list,stats}`

Outputs: `cross_links` table (DB table 20) populated with discovered inter-domain connections.

## Logic
1. `CrossDomainLinker` class in `cos/memory/crossdomain.py` with methods: `discover_links`, `add_link`, `get_links`, `stats`
2. `discover_links` scans entities and concepts across domains, finding items that appear in multiple domain contexts
3. `add_link` manually creates a cross-domain link between two items with a relationship type
4. `get_links` retrieves all cross-domain links, optionally filtered by domain or item
5. `stats` reports link counts by domain pair
6. Links stored in `cross_links` table (DB table 20) with source_id, target_id, domains, link_type, confidence

## Key Concepts
- **Cross-domain discovery**: automated detection of entities shared across domain boundaries
- **Domain bridging**: links create paths between otherwise siloed knowledge areas
- **DB table 20**: `cross_links` — stores inter-domain relationships with metadata
- **Foundation for hybrid search**: cross-domain links feed into the graph component of Phase 135's fused search

## Verification Checklist
- [x] `discover` finds cross-domain links automatically
- [x] `list` displays discovered links with domain annotations
- [x] `stats` shows link counts by domain pair
- [x] DB table `cross_links` created and populated
- [x] CETP entity correctly identified as cross-domain (cheminformatics + clinical)

## Risks (resolved)
- False positives: name-based matching could link unrelated items with similar names — confidence scoring mitigates this
- Sparse domains: few items per domain means fewer cross-domain opportunities — expected to grow as more data is ingested

## Results
| Metric | Value |
|--------|-------|
| Cross-domain links discovered | 1 (CETP: cheminformatics/clinical) |
| DB table | cross_links (table 20) |
| Domain pairs | 1 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: CETP was correctly identified as spanning cheminformatics and clinical domains, validating the cross-domain discovery logic. As more data is ingested across domains, this linking will become increasingly valuable for multi-perspective reasoning.
