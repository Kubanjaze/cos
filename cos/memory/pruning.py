"""COS memory pruning — remove stale, low-scored, or expired memory items.

Usage:
    from cos.memory.pruning import memory_pruner
    stats = memory_pruner.prune_stats()
    n = memory_pruner.prune_episodes(max_age_days=30)
    n = memory_pruner.prune_low_score("entity", threshold=0.3)
"""

import sqlite3
import time
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.pruning")


class MemoryPruner:
    """Prunes stale and low-value memory items."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def prune_episodes(self, max_age_days: int = 30, min_cost: float = 0.0) -> int:
        """Remove old episodes with cost <= min_cost. Returns count deleted."""
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%S",
                               time.localtime(time.time() - max_age_days * 86400))
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM episodes WHERE created_at < ? AND cost_usd <= ?",
                (cutoff, min_cost),
            )
            deleted = conn.execute("SELECT changes()").fetchone()[0]
        logger.info(f"Pruned {deleted} episodes older than {max_age_days} days")
        return deleted

    def prune_low_score(self, target_type: str, threshold: float = 0.3) -> int:
        """Remove items below score threshold. Returns count deleted."""
        conn = self._get_conn()
        # Get IDs to prune from memory_scores
        rows = conn.execute(
            "SELECT target_id FROM memory_scores WHERE target_type=? AND composite_score < ?",
            (target_type, threshold),
        ).fetchall()

        if not rows:
            conn.close()
            return 0

        ids = [r[0] for r in rows]
        deleted = 0

        # Delete from source table
        table_map = {
            "entity": "entities", "concept": "concepts",
            "relation": "entity_relations", "episode": "episodes",
        }
        table = table_map.get(target_type)
        if table:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", ids)
            deleted = conn.execute("SELECT changes()").fetchone()[0]

        # Delete scores
        conn.execute(
            f"DELETE FROM memory_scores WHERE target_type=? AND composite_score < ?",
            (target_type, threshold),
        )

        conn.commit()
        conn.close()
        logger.info(f"Pruned {deleted} {target_type} items below score {threshold}")
        return deleted

    def prune_stale_cache(self) -> int:
        """Clear expired cache entries."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            try:
                conn.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
                deleted = conn.execute("SELECT changes()").fetchone()[0]
            except Exception:
                deleted = 0
        logger.info(f"Pruned {deleted} expired cache entries")
        return deleted

    def dry_run(self, target_type: str, threshold: float = 0.3) -> list[dict]:
        """Preview what would be pruned without deleting."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT target_id, composite_score FROM memory_scores "
            "WHERE target_type=? AND composite_score < ? ORDER BY composite_score",
            (target_type, threshold),
        ).fetchall()
        conn.close()
        return [{"id": r[0], "score": r[1]} for r in rows]

    def prune_stats(self) -> dict:
        """Stats on pruning candidates."""
        conn = self._get_conn()
        result = {}

        # Low-score candidates (below 0.3)
        by_type = conn.execute(
            "SELECT target_type, COUNT(*) FROM memory_scores WHERE composite_score < 0.3 GROUP BY target_type"
        ).fetchall()
        result["low_score_candidates"] = {t: c for t, c in by_type}

        # Expired cache
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            expired = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at < ?", (now,)
            ).fetchone()[0]
        except Exception:
            expired = 0
        result["expired_cache"] = expired

        # Total scores
        total = conn.execute("SELECT COUNT(*) FROM memory_scores").fetchone()[0]
        result["total_scored"] = total

        conn.close()
        return result


# Singleton
memory_pruner = MemoryPruner()
