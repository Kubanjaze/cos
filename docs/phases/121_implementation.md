# Phase 121 — Document Store (Raw + Parsed Text)

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Build a document store in the memory package that persists both raw and parsed text for ingested documents. Extends Phase 105 artifacts with chunked text storage — the foundation for embedding and retrieval (Phase 122). First module in `cos/memory/`.

CLI: `python -m cos docs list [--investigation <id>]` / `python -m cos docs show <doc_id>`

Outputs: Document records in SQLite `documents` table, text chunks in `document_chunks` table

## Logic
1. Create `cos/memory/documents.py` with `DocumentStore` class
2. `documents` table: id, artifact_id, title, source_path, content_text, char_count, chunk_count, investigation_id, created_at
3. `document_chunks` table: id, document_id, chunk_index, chunk_text, char_count
4. `store_document(artifact_id, investigation_id)` — loads artifact text, splits into chunks, stores both
5. Chunking: split by paragraph (double newline), merge small paragraphs up to max_chunk_size (500 chars)
6. `get_document(doc_id)` — returns document metadata + chunk count
7. `get_chunks(doc_id)` — returns all chunks for a document
8. `search_text(query, investigation_id)` — basic substring search across chunks

## Key Concepts
- **Document = artifact + parsed text + chunks**: extends Phase 105 artifacts with structured text
- **Chunking strategy**: paragraph-based with merge — balances granularity vs context
- **Two tables**: documents (metadata) + document_chunks (text segments)
- **Track B foundation**: documents are the input to embeddings (Phase 122) and entity extraction (Phase 123)
- **Artifact linkage**: every document references an artifact_id from Phase 105

## Verification Checklist
- [ ] `store_document()` creates document from artifact
- [ ] Chunks created with paragraph-based splitting
- [ ] `get_document()` returns metadata + chunk count
- [ ] `get_chunks()` returns ordered chunks
- [ ] `search_text("KRAS")` finds matching chunks
- [ ] CLI: `docs list` and `docs show <id>` work

## Risks
- Chunk size balance: too small = lost context, too large = poor retrieval — 500 chars is a reasonable start
- Large documents: chunking is O(n) in text length — acceptable for v0
- Duplicate documents: artifact dedup (Phase 105) prevents duplicate ingestion
