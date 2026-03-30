# Phase 131 — Conflict Detection (Contradictions)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Detect contradictions in COS memory — conflicting facts, duplicate concepts with different definitions, or entities with inconsistent relations. Answers "where does knowledge disagree?"

CLI: `python -m cos conflicts {scan,list,resolve,stats}`

Outputs: Conflict records in SQLite `conflicts` table (table 18)

## Logic
1. `conflicts` table: id, conflict_type, item_a_type, item_a_id, item_b_type, item_b_id, description, severity, status, resolution, investigation_id, created_at, resolved_at
2. `scan()` — detect conflicts across memory: duplicate concepts, contradictory relations, confidence disagreements
3. `list_conflicts()` — list detected conflicts with optional status/type filters
4. `resolve(conflict_id, resolution)` — mark a conflict as resolved with explanation
5. `stats()` — total, by type, by severity, by status

## Key Concepts
- **Conflict types**: duplicate_concept, contradictory_relation, confidence_disagreement, stale_definition
- **Severity levels**: low, medium, high
- **Status**: open, resolved, ignored
- **Scan detects**: same concept name across domains with different definitions, same entity with conflicting activity values, low-confidence items contradicting high-confidence ones

## Verification Checklist
- [ ] `scan()` detects conflicts in existing data
- [ ] `list_conflicts()` returns detected conflicts
- [ ] `resolve(id, "kept higher confidence version")` marks resolved
- [ ] `stats()` shows totals by type/severity/status
- [ ] CLI: conflicts scan/list/resolve/stats all work

## Risks
- False positives: legitimate cross-domain concept differences flagged as conflicts
- Scan performance: queries multiple tables — acceptable at current scale
