# Phase 136 — Memory Snapshot System

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-30

## Goal
Capture point-in-time snapshots of the entire memory state for auditing, comparison, and rollback support. Each snapshot records table counts and metadata as a JSON state dump.

CLI: `python -m cos snapshot {create,list,show,stats}`

Outputs: `memory_snapshots` table (DB table 21) storing JSON state dumps.

## Logic
1. `SnapshotManager` class in `cos/memory/snapshots.py` with methods: `create`, `get`, `list`, `compare`, `stats`
2. `create` captures current state of all memory tables as a JSON document (row counts, timestamps, metadata)
3. `get` retrieves a specific snapshot by ID
4. `list` shows all snapshots with timestamps and summary info
5. `compare` diffs two snapshots to show what changed between them
6. `stats` provides snapshot count and storage metrics
7. Snapshots stored in `memory_snapshots` table (DB table 21) with id, created_at, state JSON

## Key Concepts
- **Point-in-time capture**: JSON state dumps record the full memory system state
- **Snapshot comparison**: diff two snapshots to see what changed (items added/removed/modified)
- **DB table 21**: `memory_snapshots` — stores serialized state with timestamps
- **Audit trail**: snapshots provide a history of how the memory system evolved over time

## Verification Checklist
- [x] `create` captures state of all 9 memory tables
- [x] `list` shows snapshots with timestamps
- [x] `show` displays a specific snapshot's contents
- [x] `stats` reports snapshot count
- [x] DB table `memory_snapshots` created and populated

## Risks (resolved)
- Storage growth: JSON snapshots can be large — mitigated by capturing counts/metadata rather than full row data
- Schema drift: snapshot format should be versioned to handle table schema changes

## Results
| Metric | Value |
|--------|-------|
| Snapshots created | 1 |
| Tables captured | 9 |
| DB table | memory_snapshots (table 21) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: A single snapshot successfully captured counts for all 9 memory tables, providing a baseline for future comparison. The compare feature will become valuable as the memory system evolves across investigation runs.
