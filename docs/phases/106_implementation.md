# Phase 106 — Metadata Tagging System (Source, Domain, Time)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Add flexible key-value metadata tags to artifacts for contextualization and retrieval. Completes Gate 1: ingest → normalize → store → tag → retrieve by metadata.

CLI: `python -m cos tag <id> --domain <d> --tags <t1,t2>` / `python -m cos search --domain <d> --tag <t>`

Outputs: Tags in SQLite `artifact_tags` table, searchable via CLI

## Logic
1. `artifact_tags` table: artifact_id, key, value (unique constraint on triplet)
2. Standard keys: domain, source, tag, description — plus arbitrary extras via **kwargs
3. Partial ID resolution: `4115f198` matches full UUID
4. `search_artifacts()` joins artifacts + tags with filter conditions
5. CLI: `tag` adds tags, `search` queries by domain/tag/source

## Key Concepts
- **Flexible key-value tags**: not a fixed schema — any key/value pair
- **Partial ID resolution**: first 8 chars of UUID sufficient for CLI use
- **UNIQUE constraint**: prevents duplicate tags (INSERT OR IGNORE)
- **JOIN queries**: search_artifacts joins artifacts + artifact_tags for filtered retrieval
- **Gate 1 complete**: all 5 steps verified (ingest → normalize → store → tag → retrieve)

## Verification Checklist
- [x] `tag_artifact()` adds 5 tags (domain, description, 3 tag values)
- [x] `search_artifacts(domain="cheminformatics")` returns matching artifact
- [x] `search_artifacts(tag="CETP")` filters correctly
- [x] Partial ID resolution works (8-char prefix)
- [x] CLI `tag` and `search` subcommands work
- [x] Gate 1 complete: full ingest→tag→retrieve flow verified

## Risks (resolved)
- Artifact ID must exist: validated with _resolve_artifact_id before tagging
- Tag search performance: indexed on (key, value) and artifact_id
- Inconsistent tag naming: convention-based (not enforced) — acceptable for v0

## Results
| Metric | Value |
|--------|-------|
| Tags added | 5 (domain, description, 3 tag values) |
| Search by domain | 1 result (cheminformatics) |
| Search by tag | 1 result (CETP) |
| DB table | artifact_tags (indexed on key/value + artifact_id) |
| Gate 1 | ✅ COMPLETE |
| Cost | $0.00 |

Key finding: Gate 1 is complete — COS can now ingest a file, normalize it, store with content-addressable hashing, tag with flexible metadata, and retrieve by domain/tag/source queries. This is the minimum viable data pipeline.
