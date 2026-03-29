# Phase 122 — Embedding Pipeline (Chunking + Indexing)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build an embedding pipeline that converts document chunks into vector embeddings for semantic search. Uses sentence-transformers for local embedding (no API cost). Stores embeddings in SQLite for retrieval.

CLI: `python -m cos embed <doc_id>` / `python -m cos embed search <query>`

Outputs: Embeddings in SQLite `chunk_embeddings` table, semantic search results

## Logic
1. Create `cos/memory/embeddings.py` with `EmbeddingPipeline` class
2. `embed_document(doc_id)` — loads chunks from Phase 121, computes embeddings, stores
3. `chunk_embeddings` table: chunk_id, embedding_blob (numpy bytes), model_name, created_at
4. `search(query, top_k=5)` — embed query, compute cosine similarity against all embeddings, return top-k
5. Model: `all-MiniLM-L6-v2` (22M params, fast, good quality)
6. Embedding storage: numpy array serialized as bytes in SQLite BLOB column
7. Cosine similarity: `np.dot(a, b) / (norm(a) * norm(b))`

## Key Concepts
- **sentence-transformers**: local embedding model, no API cost
- **all-MiniLM-L6-v2**: 384-dim embeddings, ~80MB download on first use
- **BLOB storage**: embeddings as numpy bytes in SQLite (simple, no vector DB needed)
- **Cosine similarity**: standard metric for embedding similarity
- **Semantic search**: query embedded → compared against all chunk embeddings → top-k returned
- **ADR-002 compliance**: SQLite + filesystem, no vector DB dependency

## Verification Checklist
- [ ] `embed_document()` creates embeddings for all chunks
- [ ] Embeddings stored in SQLite as BLOBs
- [ ] `search("KRAS potency")` returns relevant chunks
- [ ] Cosine similarity scores in [0, 1] range
- [ ] Top-k results ordered by relevance
- [ ] CLI: embed + embed search work

## Risks
- First run downloads ~80MB model — one-time cost
- Embedding all chunks is O(n) — acceptable for v0 document counts
- SQLite BLOB search requires loading all embeddings into memory — fine for <10K chunks
- sentence-transformers requires torch — significant dependency
