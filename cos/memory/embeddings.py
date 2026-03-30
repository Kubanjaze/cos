"""COS embedding pipeline — vector embeddings for semantic search.

Converts document chunks into embeddings using sentence-transformers.
Stores in SQLite, searches by cosine similarity.

Usage:
    from cos.memory.embeddings import embedding_pipeline
    embedding_pipeline.embed_document("doc-abc123")
    results = embedding_pipeline.search("KRAS potency", top_k=5)
"""

import os
import sqlite3
import time
from typing import Optional

import numpy as np

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.embeddings")

DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingPipeline:
    """Embedding pipeline with SQLite storage and cosine search."""

    def __init__(self, db_path: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        self._db_path = db_path or settings.db_path
        self._model_name = model_name
        self._model = None  # lazy load
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emb_document ON chunk_embeddings(document_id)")

    def _get_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                )
        return self._model

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts into embeddings."""
        model = self._get_model()
        return model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    def embed_document(self, doc_id: str) -> int:
        """Embed all chunks of a document. Returns number of embeddings created."""
        from cos.memory.documents import document_store

        doc = document_store.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        chunks = document_store.get_chunks(doc.id)
        if not chunks:
            logger.warning(f"No chunks for document {doc.id}")
            return 0

        texts = [c.chunk_text for c in chunks]
        embeddings = self._encode(texts)

        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        created = 0

        for chunk, emb in zip(chunks, embeddings):
            emb_bytes = emb.astype(np.float32).tobytes()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO chunk_embeddings (chunk_id, document_id, embedding, model_name, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (chunk.id, doc.id, emb_bytes, self._model_name, ts),
                )
                created += 1
            except Exception as e:
                logger.error(f"Failed to store embedding for chunk {chunk.id}: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Embedded document {doc.id}: {created} chunks, dim={embeddings.shape[1]}")
        return created

    def search(self, query: str, top_k: int = 5, investigation_id: Optional[str] = None) -> list[dict]:
        """Semantic search across all embeddings. Returns top-k results by cosine similarity."""
        query_emb = self._encode([query])[0]

        conn = self._get_conn()

        if investigation_id:
            rows = conn.execute(
                "SELECT e.chunk_id, e.document_id, e.embedding "
                "FROM chunk_embeddings e JOIN documents d ON e.document_id = d.id "
                "WHERE d.investigation_id = ?",
                (investigation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chunk_id, document_id, embedding FROM chunk_embeddings"
            ).fetchall()

        if not rows:
            conn.close()
            return []

        # Compute cosine similarities
        results = []
        query_norm = np.linalg.norm(query_emb)

        for chunk_id, document_id, emb_bytes in rows:
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            sim = np.dot(query_emb, emb) / (query_norm * np.linalg.norm(emb) + 1e-8)
            results.append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "similarity": round(float(sim), 4),
            })

        # Sort by similarity, return top-k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = results[:top_k]

        # Enrich with chunk text
        from cos.memory.documents import document_store
        for r in top_results:
            chunk_row = conn.execute(
                "SELECT chunk_text FROM document_chunks WHERE id=?", (r["chunk_id"],)
            ).fetchone()
            r["text"] = chunk_row[0][:200] if chunk_row else ""

        conn.close()
        return top_results

    def stats(self) -> dict:
        """Get embedding statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
        docs = conn.execute("SELECT COUNT(DISTINCT document_id) FROM chunk_embeddings").fetchone()[0]
        conn.close()
        return {"total_embeddings": total, "documents_embedded": docs, "model": self._model_name}


# Singleton
embedding_pipeline = EmbeddingPipeline()
