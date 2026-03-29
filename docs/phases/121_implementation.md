# Phase 121 — Document Store (Raw + Parsed Text)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Persistent document store with paragraph-based chunking. Extends artifacts with structured text storage — foundation for embedding and retrieval. First `cos/memory/` module.

CLI: `python -m cos docs {list,show,store,search}`

Outputs: `documents` + `document_chunks` tables in SQLite

## Logic
1. `store_document(artifact_id)` loads artifact text, chunks by paragraph (max 500 chars), stores both
2. `documents` table: metadata (id, artifact_id, title, char_count, chunk_count)
3. `document_chunks` table: ordered text segments (id, document_id, chunk_index, chunk_text)
4. `search_text(query)` does substring search across chunks with JOIN to documents
5. Paragraph-based chunking: split on `\n\n`, merge small paragraphs up to max_size

## Key Concepts
- **Document = artifact + structured text**: extends Phase 105 with chunked storage
- **Paragraph chunking**: split on double newline, merge small, hard-split oversized
- **Two tables**: documents (metadata) + document_chunks (text segments)
- **Substring search**: basic LIKE query across chunks — semantic search in Phase 122
- **Track B foundation**: chunks are the input to embeddings (Phase 122)

## Verification Checklist
- [x] `store_document()` creates doc from compounds.csv artifact: 7 chunks, 3289 chars
- [x] Chunks created at ~500 char max with paragraph boundaries
- [x] `get_document()` returns metadata with chunk count
- [x] `get_chunks()` returns ordered chunks
- [x] `search_text("benz_004")` finds matching chunk
- [x] CLI: docs list, docs show, docs store, docs search all work

## Risks (resolved)
- Chunk size balance: 500 chars is reasonable for markdown tables
- Large documents: O(n) chunking, acceptable at v0 scale
- Duplicate docs prevented by artifact-level dedup (Phase 105)

## Results
| Metric | Value |
|--------|-------|
| Test document | compounds.csv → 7 chunks, 3289 chars |
| Search test | "benz_004" found in chunk 0 |
| DB tables added | documents + document_chunks (tables 8-9) |
| First memory module | cos/memory/documents.py |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Paragraph-based chunking on markdown tables produces ~500 char chunks that contain 5-7 compound rows each — good granularity for retrieval. The search_text substring query is basic but functional until semantic search (Phase 122) is built.
