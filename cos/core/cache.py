"""COS cache layer — reduces cost by avoiding redundant computations.

SQLite-backed with TTL expiration and hit counting.

Usage:
    from cos.core.cache import cache_manager
    cache_manager.set("api:classify:CCO", {"class": "potent"}, ttl_seconds=3600)
    result = cache_manager.get("api:classify:CCO")  # returns cached value or None
"""

import json
import os
import sqlite3
import time
from typing import Any, Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.cache")


class CacheManager:
    """SQLite-backed cache with TTL and hit counting."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0
                )
            """)

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store a value with TTL expiration."""
        now = time.time()
        value_json = json.dumps(value, default=str)
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value_json, created_at, expires_at, hit_count) "
                "VALUES (?, ?, ?, ?, 0)",
                (key, value_json, now, now + ttl_seconds),
            )
        logger.debug(f"Cache set: {key} (TTL={ttl_seconds}s)")

    def get(self, key: str) -> Optional[Any]:
        """Get cached value. Returns None on miss or expiration."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value_json, expires_at, hit_count FROM cache WHERE key=?", (key,)
        ).fetchone()

        if not row:
            conn.close()
            return None

        value_json, expires_at, hit_count = row
        now = time.time()

        if now > expires_at:
            # Expired — clean up
            conn.execute("DELETE FROM cache WHERE key=?", (key,))
            conn.commit()
            conn.close()
            logger.debug(f"Cache expired: {key}")
            return None

        # Cache hit — increment counter
        conn.execute("UPDATE cache SET hit_count=? WHERE key=?", (hit_count + 1, key))
        conn.commit()
        conn.close()
        return json.loads(value_json)

    def invalidate(self, key: str) -> bool:
        """Remove a specific cache entry. Returns True if removed."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM cache WHERE key=?", (key,))
            return cursor.rowcount > 0

    def clear(self) -> int:
        """Remove all cache entries. Returns count removed."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM cache")
            count = cursor.rowcount
        logger.info(f"Cache cleared: {count} entries removed")
        return count

    def stats(self) -> dict:
        """Get cache statistics."""
        conn = self._get_conn()
        now = time.time()
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        expired = conn.execute("SELECT COUNT(*) FROM cache WHERE expires_at < ?", (now,)).fetchone()[0]
        active = total - expired
        total_hits = conn.execute("SELECT COALESCE(SUM(hit_count), 0) FROM cache").fetchone()[0]
        conn.close()
        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": expired,
            "total_hits": total_hits,
        }


# Singleton
cache_manager = CacheManager()
