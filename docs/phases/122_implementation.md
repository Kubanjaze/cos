# Phase 122 — Embedding Pipeline (Chunking + Indexing)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Vector embedding pipeline for semantic search over document chunks. Uses sentence-transformers locally (no API cost). Stores embeddings as SQLite BLOBs.

CLI: `python -m cos embed doc <id>` / `python -m cos embed search <query>` / `python -m cos embed stats`

Outputs: Embeddings in SQLite `chunk_embeddings` table

## Logic
1. `embed_document(doc_id)` loads chunks from Phase 121, encodes with sentence-transformers, stores as BLOBs
2. `search(query, top_k)` encodes query, computes cosine similarity against all stored embeddings
3. Model: all-MiniLM-L6-v2 (384-dim, ~80MB, lazy-loaded on first use)
4. Embedding storage: numpy float32 → tobytes() → SQLite BLOB
5. Retrieval: load all BLOBs, frombuffer, dot product / norms

## Key Concepts
- **sentence-transformers**: local embedding, zero API cost
- **all-MiniLM-L6-v2**: 384 dimensions, good balance of speed/quality
- **BLOB storage**: numpy bytes in SQLite — no vector DB dependency (ADR-002)
- **Cosine similarity**: `dot(a,b) / (norm(a) * norm(b))` for ranking
- **Lazy model loading**: model downloaded/loaded only on first use

## Deviations from Plan
- Similarity scores are low (0.19 max) because chunks are markdown tables, not natural text — expected for structured data

## Verification Checklist
- [x] `embed_document()` creates 7 embeddings from compounds doc
- [x] Embeddings stored as BLOBs in chunk_embeddings table (384-dim float32)
- [x] `search("potent CETP inhibitor")` returns ranked results
- [x] Cosine similarity scores computed correctly (0.19, 0.18, 0.17)
- [x] `embed stats` shows 7 embeddings, 1 document
- [x] CLI: embed doc, embed search, embed stats all work

## Risks (resolved)
- Model download: ~80MB on first use, cached locally after
- BLOB scan for search: loads all embeddings into memory — fine for <10K chunks
- Low similarity on structured data: expected — natural text would score higher
- sentence-transformers requires torch: significant dependency (~2GB)

## Results
| Metric | Value |
|--------|-------|
| Chunks embedded | 7 |
| Embedding dim | 384 |
| Model | all-MiniLM-L6-v2 |
| Top search result | sim=0.1910 (compound data with NO2/Me) |
| DB table | chunk_embeddings (table 10) |
| API cost | $0.00 (local model) |

Key finding: Semantic search works even on markdown table data, though similarity scores are lower than for natural text. The pipeline is ready for richer documents (papers, reports) where semantic retrieval will shine. BLOB storage in SQLite is simple and sufficient — no vector DB needed at this scale.
