# Phase 108 — Storage Abstraction (Local → Cloud-Ready)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Create a storage abstraction wrapping file and database operations behind protocol interfaces. Local-first (ADR-002), but swappable to cloud backends (S3 + Postgres) by implementing the same protocol.

CLI: `python -m cos storage`

Outputs: `storage` singleton accessible via `from cos.core.storage import storage`

## Logic
1. `FileStorageProtocol`: save(key, data), load(key), exists(key), delete(key), list_keys(prefix)
2. `LocalFileStorage(base_dir)`: filesystem implementation with nested directory support
3. `DatabaseProtocol`: execute(sql, params), fetchone(sql, params), fetchall(sql, params)
4. `SQLiteDatabase(db_path)`: wraps sqlite3 with context-managed connections
5. `Storage` combines both: `storage.files` + `storage.db`
6. `storage.info()` returns backend type, paths, sizes, table list

## Key Concepts
- **Protocol pattern**: `@runtime_checkable` Protocol classes define the interface
- **LocalFileStorage**: save/load/exists/delete/list_keys over filesystem
- **SQLiteDatabase**: execute/fetchone/fetchall + tables() + size_bytes()
- **Storage singleton**: `storage = Storage(files=LocalFileStorage(...), db=SQLiteDatabase(...))`
- **Cloud migration path**: implement S3Storage(Protocol) and PostgresDB(Protocol), swap in Storage()
- **No code changes needed in calling modules** when backend changes

## Verification Checklist
- [x] `storage.files.save("test/hello.txt", b"Hello COS!")` creates file
- [x] `storage.files.load("test/hello.txt")` returns b"Hello COS!"
- [x] `storage.files.exists()` returns True/False correctly
- [x] `storage.files.delete()` removes file
- [x] `storage.files.list_keys("test/")` returns matching keys
- [x] `storage.db.tables()` returns all 4 COS tables
- [x] `python -m cos storage` shows backend info, file count, DB size

## Risks (resolved)
- Over-abstraction: kept interfaces minimal (5 methods for files, 3 for DB)
- SQLite connection per call: acceptable for local-first; connection pooling deferred
- Path separator differences (Windows vs Unix): Path handles this transparently

## Results
| Metric | Value |
|--------|-------|
| File ops | save, load, exists, delete, list_keys — all verified |
| DB ops | execute, fetchone, fetchall, tables, size_bytes — all verified |
| Files in storage | 6 (artifacts + logs + tasks) |
| DB size | 61,440 bytes |
| DB tables | artifact_tags, artifacts, cost_events, tasks |
| External deps | 0 (stdlib only) |
| Cost | $0.00 |

Key finding: The Protocol pattern gives us a clean cloud migration path with zero calling-code changes. The `storage.info()` method provides instant visibility into what's stored where — essential for debugging and system monitoring.
