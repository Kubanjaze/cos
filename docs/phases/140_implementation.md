# Phase 140 — Memory Visualization

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Provide visualization tools for exploring the memory system's structure. Includes ASCII tree views, domain clustering, entity type distribution, graph export, and a memory map showing all data stores. Completes Track B (Memory System, Phases 121-140).

CLI: `python -m cos viz {tree,map,clusters,export,stats}`

Outputs: No new DB table. Generates ASCII output and JSON graph export.

## Logic
1. `MemoryVisualization` class in `cos/memory/visualization.py` with methods: `graph_ascii`, `domain_clusters`, `entity_type_distribution`, `export_graph`, `memory_map`, `stats`
2. `graph_ascii` renders an entity and its relations as an ASCII tree (indented text)
3. `domain_clusters` groups entities by domain and displays cluster membership
4. `entity_type_distribution` shows counts by entity type
5. `export_graph` serializes the entity-relation graph to JSON for external visualization tools
6. `memory_map` provides a high-level overview of all memory data stores with item counts
7. `stats` reports visualization-related metrics

## Key Concepts
- **ASCII visualization**: terminal-friendly tree rendering without external GUI dependencies
- **Domain clustering**: groups entities by domain for structural overview
- **Graph export**: JSON serialization enables use with external tools (Gephi, D3.js, etc.)
- **Memory map**: single-view summary of all 10 data stores in the memory system
- **Track B capstone**: this phase completes the Memory System track (20/20 phases)

## Verification Checklist
- [x] `tree` renders ASCII tree for a given entity (benz scaffold, 11 compounds)
- [x] `map` shows memory map with 10 data stores
- [x] `clusters` displays domain clustering
- [x] `export` produces valid JSON graph output
- [x] `stats` reports visualization metrics
- [x] All Track B phases (121-140) complete and integrated

## Risks (resolved)
- Large graphs: ASCII rendering could be unwieldy for many entities — tree view is scoped to a single entity and its neighbors
- No GUI: CLI-only visualization is limited but aligns with ADR-001 (local-first CLI toolkit)

## Results
| Metric | Value |
|--------|-------|
| ASCII tree | benz scaffold with 11 compounds |
| Memory map | 10 data stores displayed |
| Domain clusters | Verified |
| JSON export | Verified |
| Track B status | COMPLETE (20/20 phases) |
| New DB tables | 0 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The memory visualization suite provides multiple lenses into the memory system — from fine-grained entity trees to high-level memory maps. With Track B now complete (Phases 121-140), the COS memory system has full CRUD, scoring, pruning, cross-domain linking, hybrid search, snapshots, change tracking, external connectors, gap detection, and visualization capabilities.
