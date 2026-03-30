# Phase 131 — Conflict Detection (Contradictions)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Detect contradictions in COS memory — conflicting facts, duplicate concepts with different definitions, or entities with inconsistent relations.

CLI: `python -m cos conflicts {scan,list,resolve,stats}`

Outputs: Conflict records in SQLite `conflicts` table (table 18)

## Logic
1. `conflicts` table: 13 columns incl. conflict_type, severity, status, resolution
2. `scan()` runs 3 detectors: duplicate_concept, contradictory_relation, confidence_disagreement
3. `list_conflicts()` with status/type/severity filters
4. `resolve(conflict_id, resolution)` marks resolved with timestamp
5. `stats()` totals by type, severity, status

## Key Concepts
- **3 scan detectors**: duplicate concepts across domains, contradictory activity values, confidence gaps >0.5
- **Deduplication**: won't re-create existing open conflict for same item pair
- **Partial ID resolution**: resolve() supports partial conflict IDs

## Verification Checklist
- [x] `scan()` detects 2 conflicts after creating cross-domain CETP concept
- [x] `list_conflicts()` shows duplicate_concept + confidence_disagreement
- [x] `resolve()` marks conflict resolved with explanation
- [x] `stats()` shows 2 total, by type/severity/status
- [x] CLI: all commands work

## Results
| Metric | Value |
|--------|-------|
| Conflicts detected | 2 (duplicate_concept + confidence_disagreement) |
| DB table | conflicts (table 18) |
| Scan detectors | 3 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Cross-domain concept definitions naturally produce both duplicate and confidence conflicts, validating the multi-detector approach.
