# Phase 107 — Async Task Queue (Background Jobs)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build an async task queue for COS workflows to run as background jobs. Tasks are submitted, queued, executed by a worker, and results captured — all backed by SQLite.

CLI: `python -m cos task submit "cos info"` / `task list` / `task status <id>` / `task run`

Outputs: Task records in SQLite `tasks` table, results in `~/.cos/tasks/{id}.txt`

## Logic
1. `TaskQueue` class with SQLite backend in `cos/core/tasks.py`
2. `tasks` table: id, status, command, investigation_id, submitted_at, started_at, completed_at, result_path, error
3. `submit()` creates pending task, `run_next()` picks oldest pending and executes via subprocess
4. Command parsing: "cos X" → `python -m cos X`; captures stdout/stderr to result file
5. `run_worker(max_tasks)` loops until queue empty or max reached
6. 300s timeout per task; failed tasks capture error message

## Key Concepts
- **SQLite-backed queue**: no external broker (Redis/Celery) needed — pure local-first (ADR-001/002)
- **Sequential worker**: tasks processed one-at-a-time; concurrency deferred to later phase
- **Subprocess isolation**: each task runs in a separate Python process
- **Result capture**: stdout + stderr + exit code saved to `~/.cos/tasks/{task_id}.txt`
- **Partial ID resolution**: 8-char prefix sufficient for task lookup
- **Status lifecycle**: pending → running → completed | failed

## Verification Checklist
- [x] `submit("cos info")` creates task with pending status
- [x] `run_next()` picks oldest pending, executes, marks completed
- [x] `task list` shows ID, status, investigation, submitted time, command
- [x] `task status <id>` shows full detail including captured stdout
- [x] Task result file contains "COS — Cognitive Operating System v0.1.0" (from `cos info`)
- [x] Worker processes 1 task and reports "processed 1 tasks"

## Risks (resolved)
- Subprocess command injection: tasks run via split() not shell=True — safe for known commands
- Long-running tasks: 300s timeout prevents infinite hangs
- argparse `command` naming conflict: fixed by using `task_cmd` for submit positional arg

## Results
| Metric | Value |
|--------|-------|
| Task lifecycle | submit → pending → running → completed (full cycle verified) |
| Result capture | stdout + stderr + exit code saved to file |
| Execution time | ~1 second for `cos info` |
| DB table | tasks (indexed on status + investigation_id) |
| External deps | 0 (subprocess + sqlite3 are stdlib) |
| Cost | $0.00 |

Key finding: A SQLite-backed task queue is surprisingly capable for single-user local-first systems. No Redis/Celery overhead, tasks persist across sessions, and results are inspectable. The sequential worker is sufficient for v0 — parallel execution can be added later without changing the queue interface.
