# Phase 105 — File Ingestion Service (PDF, CSV, TXT)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-27

## Goal
Build a file ingestion service that normalizes inputs into a common document format with content-addressable storage. Entry point for all data flowing into COS. Gate 1 checkpoint: ingest → store → retrieve.

CLI: `python -m cos ingest <file> [--investigation <id>]` / `python -m cos artifacts [--investigation <id>]`

Outputs: Artifact records in SQLite, normalized text in `~/.cos/artifacts/{hash}.txt`

## Logic
1. Accept file path + investigation_id; detect type by extension
2. Extract text: TXT→direct read, CSV→pandas→markdown table, PDF→pdfplumber (optional)
3. Hash content (SHA-256) for deduplication
4. Store normalized text at `~/.cos/artifacts/{hash}.txt`
5. Insert Artifact record in SQLite `artifacts` table
6. Duplicate detection: if hash exists, return existing artifact without re-writing

## Key Concepts
- **Artifact schema**: id (UUID), type, uri, hash (SHA-256), schema_version, created_at, investigation_id, size_bytes, stored_path
- **Content-addressable storage**: files stored by hash — automatic deduplication
- **Handler pattern**: `HANDLERS = {".txt": fn, ".csv": fn, ".pdf": fn}` — extensible for new formats
- **SQLite artifacts table**: indexed on hash + investigation_id
- **Gate 1 progress**: ingest (✅) → normalize (✅) → store (✅) → tag (Phase 106) → retrieve (Phase 106)

## Verification Checklist
- [x] TXT file ingested and stored (43 bytes)
- [x] CSV file ingested, converted to markdown table (3289 bytes)
- [x] Artifact record in SQLite with correct SHA-256 hash
- [x] Normalized text at `~/.cos/artifacts/{hash}.txt`
- [x] Duplicate detection: second ingest of same file returns existing artifact
- [x] `python -m cos ingest <file>` CLI works
- [x] `python -m cos artifacts` lists all with ID, type, size, investigation
- [x] Investigation linkage works (--investigation flag)

## Risks (resolved)
- PDF requires pdfplumber: made optional with fallback to raw text read
- Large files: deferred chunking to Phase 122 (embedding pipeline)
- SHA-256 collision: effectively impossible at our scale

## Results
| Metric | Value |
|--------|-------|
| File types supported | TXT, CSV, PDF, MD, JSON |
| TXT test | 43 bytes, hash 1c67ddd2... |
| CSV test | compounds.csv → 3289 bytes markdown |
| Dedup test | Same CSV → returned existing artifact (no re-write) |
| DB tables added | artifacts (with hash + investigation indexes) |
| Cost | $0.00 |

Key finding: Content-addressable storage with SHA-256 hashing provides free deduplication. The CSV→markdown conversion preserves table structure in a text-searchable format that's ready for embedding (Phase 122).
