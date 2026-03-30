"""COS memory scoring — relevance + confidence scoring for memory items.

Computes composite scores across all memory types to answer "what matters most?"

Usage:
    from cos.memory.scoring import memory_scorer
    memory_scorer.score_all("entity")
    top = memory_scorer.get_top("entity", limit=10)
"""

import sqlite3
import time
import uuid
import math
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.scoring")

# Weights for composite score
W_RELEVANCE = 0.3
W_CONFIDENCE = 0.3
W_RECENCY = 0.2
W_FREQUENCY = 0.2


@dataclass
class MemoryScore:
    id: str
    target_type: str
    target_id: str
    relevance: float
    confidence: float
    recency: float
    frequency: int
    composite_score: float
    investigation_id: str
    created_at: str
    updated_at: str


def compute_composite(relevance: float, confidence: float, recency: float, frequency: int) -> float:
    """Weighted composite: relevance*0.3 + confidence*0.3 + recency*0.2 + freq_norm*0.2."""
    freq_norm = min(1.0, math.log1p(frequency) / 5.0)  # log-scale, cap at ~148 accesses
    return round(
        W_RELEVANCE * relevance + W_CONFIDENCE * confidence +
        W_RECENCY * recency + W_FREQUENCY * freq_norm, 4
    )


class MemoryScorer:
    """Unified scoring for all memory types."""

    _COLS = (
        "id, target_type, target_id, relevance, confidence, recency, frequency, "
        "composite_score, investigation_id, created_at, updated_at"
    )

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_scores (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relevance REAL NOT NULL DEFAULT 0.5,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    recency REAL NOT NULL DEFAULT 1.0,
                    frequency INTEGER NOT NULL DEFAULT 0,
                    composite_score REAL NOT NULL DEFAULT 0.5,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(target_type, target_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_type ON memory_scores(target_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_score ON memory_scores(composite_score DESC)")

    def score_all(self, target_type: str) -> int:
        """Score all items of a given type. Returns count scored."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        scored = 0

        if target_type == "entity":
            rows = conn.execute(
                "SELECT id, confidence, investigation_id FROM entities"
            ).fetchall()
            for eid, conf, inv in rows:
                scored += self._upsert_score(conn, "entity", eid, conf, conf, inv, ts)

        elif target_type == "concept":
            rows = conn.execute(
                "SELECT id, confidence, investigation_id FROM concepts"
            ).fetchall()
            for cid, conf, inv in rows:
                scored += self._upsert_score(conn, "concept", cid, conf, conf, inv, ts)

        elif target_type == "relation":
            rows = conn.execute(
                "SELECT id, confidence, document_id FROM entity_relations"
            ).fetchall()
            for rid, conf, doc_id in rows:
                scored += self._upsert_score(conn, "relation", rid, conf, conf, "default", ts)

        elif target_type == "episode":
            rows = conn.execute(
                "SELECT id, investigation_id FROM episodes"
            ).fetchall()
            for eid, inv in rows:
                scored += self._upsert_score(conn, "episode", eid, 0.5, 0.5, inv, ts)

        conn.commit()
        conn.close()
        logger.info(f"Scored {scored} {target_type} items")
        return scored

    def _upsert_score(self, conn, target_type, target_id, relevance, confidence, inv_id, ts) -> int:
        recency = 1.0  # Current items get full recency
        existing = conn.execute(
            "SELECT id, frequency FROM memory_scores WHERE target_type=? AND target_id=?",
            (target_type, target_id),
        ).fetchone()

        freq = existing[1] if existing else 0
        composite = compute_composite(relevance, confidence, recency, freq)

        if existing:
            conn.execute(
                "UPDATE memory_scores SET relevance=?, confidence=?, recency=?, "
                "composite_score=?, updated_at=? WHERE id=?",
                (relevance, confidence, recency, composite, ts, existing[0]),
            )
        else:
            sid = f"ms-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO memory_scores (id, target_type, target_id, relevance, confidence, "
                "recency, frequency, composite_score, investigation_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, target_type, target_id, relevance, confidence, recency, freq, composite, inv_id, ts, ts),
            )
        return 1

    def get_top(self, target_type: Optional[str] = None, limit: int = 10) -> list[MemoryScore]:
        """Return highest-scored items."""
        conn = self._get_conn()
        if target_type:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_scores WHERE target_type=? "
                f"ORDER BY composite_score DESC LIMIT ?",
                (target_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM memory_scores ORDER BY composite_score DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [MemoryScore(*r) for r in rows]

    def record_access(self, target_type: str, target_id: str) -> None:
        """Bump frequency counter for an item."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memory_scores SET frequency=frequency+1, updated_at=? "
                "WHERE target_type=? AND target_id=?",
                (ts, target_type, target_id),
            )

    def stats(self) -> dict:
        """Scoring statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memory_scores").fetchone()[0]
        avg_score = conn.execute(
            "SELECT COALESCE(AVG(composite_score), 0) FROM memory_scores"
        ).fetchone()[0]
        by_type = conn.execute(
            "SELECT target_type, COUNT(*), AVG(composite_score) FROM memory_scores GROUP BY target_type"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "avg_score": round(avg_score, 4),
            "by_type": {t: {"count": c, "avg_score": round(a, 4)} for t, c, a in by_type},
        }


# Singleton
memory_scorer = MemoryScorer()
