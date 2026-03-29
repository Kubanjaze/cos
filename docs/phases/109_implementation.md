# Phase 109 — Versioning System for Outputs + Runs

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Add per-investigation versioning so outputs are versioned (v1, v2, v3) rather than overwritten. Enables reproducibility tracking and audit trail.

CLI: `python -m cos version list <investigation_id>`

Outputs: Version records in SQLite `versions` table

## Logic
1. `VersionManager` class with SQLite backend in `cos/core/versioning.py`
2. `versions` table: id, investigation_id, version_number, artifact_id, created_at, description
3. `next_version()` auto-increments per investigation (MAX + 1)
4. `stamp()` creates version record, returns version number
5. `get_versions()` and `get_latest()` for queries
6. CLI: `version list <investigation_id>` shows ordered history

## Key Concepts
- **Per-investigation scoping**: version numbers independent per investigation (ADR-003)
- **Non-destructive**: versions append, never overwrite
- **Artifact linkage**: optional — versions can reference a specific artifact_id
- **Auto-increment**: MAX(version_number) + 1 per investigation
- **Audit trail**: timestamp + description on every version

## Verification Checklist
- [x] `next_version("inv-cetp")` returns 1 on first call
- [x] `stamp()` creates v1, v2, v3 sequentially
- [x] `get_versions()` returns ordered list (v1 → v2 → v3)
- [x] `get_latest()` returns v3 with correct description
- [x] CLI `version list inv-cetp` shows all 3 versions
- [x] Versions table created in cos.db

## Risks (resolved)
- Concurrent version stamping: MAX+1 not atomic, but local-first single-user (ADR-001) means no race condition
- Version number gaps if rows deleted: acceptable — versions are append-only

## Results
| Metric | Value |
|--------|-------|
| Versions stamped | 3 (v1: initial ingestion, v2: re-tagged, v3: analysis) |
| Latest query | v3 — "Analysis run" |
| DB table | versions (indexed on investigation_id) |
| External deps | 0 (stdlib only) |
| Cost | $0.00 |

Key finding: Per-investigation versioning is the missing link for reproducibility. Combined with content-addressable artifacts (Phase 105) and metadata tags (Phase 106), COS now has a complete audit trail: what was ingested, how it was tagged, and what version of analysis produced which outputs.
