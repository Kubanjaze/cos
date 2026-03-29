"""COS storage abstraction layer.

Wraps file and database operations behind clean interfaces.
Local-first implementation (ADR-002), cloud-swappable later.

Usage:
    from cos.core.storage import storage
    storage.files.save("artifacts/doc.txt", b"content")
    data = storage.files.load("artifacts/doc.txt")
    rows = storage.db.fetchall("SELECT * FROM artifacts")
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.storage")


# ── File Storage Protocol + Implementation ──────────────────────────────

@runtime_checkable
class FileStorageProtocol(Protocol):
    def save(self, key: str, data: bytes) -> str: ...
    def load(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def list_keys(self, prefix: str = "") -> list[str]: ...


class LocalFileStorage:
    """Filesystem-backed file storage."""

    def __init__(self, base_dir: str):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._base / key

    def save(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def load(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        search_dir = self._base / prefix if prefix else self._base
        if not search_dir.exists():
            return []
        keys = []
        for p in search_dir.rglob("*"):
            if p.is_file():
                keys.append(str(p.relative_to(self._base)))
        return sorted(keys)

    def size_bytes(self) -> int:
        total = 0
        for p in self._base.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total


# ── Database Protocol + Implementation ──────────────────────────────────

@runtime_checkable
class DatabaseProtocol(Protocol):
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor: ...
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[tuple]: ...
    def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]: ...


class SQLiteDatabase:
    """SQLite-backed database with connection management."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._conn() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[tuple]:
        with self._conn() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._conn() as conn:
            return conn.execute(sql, params).fetchall()

    def size_bytes(self) -> int:
        if os.path.exists(self._db_path):
            return os.path.getsize(self._db_path)
        return 0

    def tables(self) -> list[str]:
        rows = self.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in rows]


# ── Combined Storage ────────────────────────────────────────────────────

class Storage:
    """Combined file + database storage."""

    def __init__(self, files: LocalFileStorage, db: SQLiteDatabase):
        self.files = files
        self.db = db

    def info(self) -> dict:
        tables = self.db.tables()
        return {
            "file_backend": "LocalFileStorage",
            "file_base": str(self.files._base),
            "file_size_bytes": self.files.size_bytes(),
            "file_count": len(self.files.list_keys()),
            "db_backend": "SQLiteDatabase",
            "db_path": self.db._db_path,
            "db_size_bytes": self.db.size_bytes(),
            "db_tables": tables,
            "db_table_count": len(tables),
        }


# Singleton
storage = Storage(
    files=LocalFileStorage(settings.storage_dir),
    db=SQLiteDatabase(settings.db_path),
)
