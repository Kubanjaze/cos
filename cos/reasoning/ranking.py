"""COS ranking engine — importance scoring for reasoning outputs.

Phase 142: Ranks items by multi-factor importance scoring.
"""

import sqlite3
import time
import uuid
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.ranking")


class RankingEngine:
    """Ranks items by computed importance."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rankings (
                    id TEXT PRIMARY KEY,
                    context TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    factors_json TEXT NOT NULL DEFAULT '{}',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rank_ctx ON rankings(context)")

    def rank(self, context: str, items: list[dict], investigation_id: str = "default") -> list[dict]:
        """Rank items by importance. Each item needs: type, id, confidence, relevance."""
        import json
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = self._get_conn()

        ranked = []
        for item in items:
            conf = item.get("confidence", 0.5)
            rel = item.get("relevance", 0.5)
            freq = item.get("frequency", 0)
            import math
            freq_norm = min(1.0, math.log1p(freq) / 5.0)
            score = round(0.4 * conf + 0.35 * rel + 0.25 * freq_norm, 4)

            rid = f"rnk-{uuid.uuid4().hex[:8]}"
            factors = {"confidence": conf, "relevance": rel, "frequency": freq}
            conn.execute(
                "INSERT INTO rankings (id, context, item_type, item_id, score, factors_json, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (rid, context, item.get("type", "unknown"), item.get("id", ""), score,
                 json.dumps(factors), investigation_id, ts),
            )
            ranked.append({**item, "rank_score": score, "rank_id": rid})

        conn.commit()
        conn.close()

        ranked.sort(key=lambda x: x["rank_score"], reverse=True)
        for i, r in enumerate(ranked):
            r["rank"] = i + 1

        logger.info(f"Ranked {len(ranked)} items for '{context}'")
        return ranked

    def get_rankings(self, context: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT item_type, item_id, score FROM rankings WHERE context=? ORDER BY score DESC",
            (context,),
        ).fetchall()
        conn.close()
        return [{"type": r[0], "id": r[1], "score": r[2]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM rankings").fetchone()[0]
        contexts = conn.execute("SELECT COUNT(DISTINCT context) FROM rankings").fetchone()[0]
        conn.close()
        return {"total_rankings": total, "contexts": contexts}


ranking_engine = RankingEngine()
