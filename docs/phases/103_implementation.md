# Phase 103 — Logging + Tracing Layer (Per Workflow + Cost)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-27

## Goal
Build a structured logging system for COS with dual output: human-readable console + JSON lines file. Every operation is observable with trace IDs and cost annotations.

CLI: Any COS command emits logs. Direct test via `from cos.core.logging import get_logger`.

Outputs: JSON log files in `~/.cos/logs/cos.log` (daily rotation, 30 day retention)

## Logic
1. `JsonFormatter`: JSON lines with timestamp, level, module, message, + optional trace_id/cost/tokens
2. `ConsoleFormatter`: `HH:MM:SS LEVEL module: message [trace_id] ($cost)`
3. `get_logger(name)`: factory that ensures root logger is configured once (singleton pattern)
4. Root logger: console (stderr) + file (TimedRotatingFileHandler, midnight rotation)
5. Log level from `settings.log_level`

## Key Concepts
- **Dual output**: console for humans, JSON lines for machines (same log events)
- **Structured fields**: trace_id, cost, investigation_id, workflow_id, tokens, duration_ms — all optional `extra={}` params
- **TimedRotatingFileHandler**: daily rotation, 30 backups
- **Lazy init**: `_setup_root_logger()` called once on first `get_logger()` — avoids import-time side effects
- **stdlib only**: no external logging libraries

## Verification Checklist
- [x] `get_logger("cos.test")` returns configured logger
- [x] Console output: `16:33:01 INFO cos.test: message [trace] ($cost)` format
- [x] File output: JSON lines with all structured fields
- [x] trace_id and cost appear in both console and file
- [x] Log files created in ~/.cos/logs/cos.log
- [x] Daily rotation configured (midnight, 30 backups)

## Risks (resolved)
- Log directory creation: handled with `mkdir(parents=True, exist_ok=True)`
- File handler failure (permissions): caught with try/except, falls back to console-only
- JSON serialization: `default=str` handles non-standard types

## Results
| Metric | Value |
|--------|-------|
| Formatters | 2 (JsonFormatter, ConsoleFormatter) |
| Structured fields | 6 (trace_id, cost, investigation_id, workflow_id, tokens, duration_ms) |
| Rotation | Daily, 30 day retention |
| External deps | 0 (stdlib only) |
| Cost | $0.00 |

Key finding: The dual-output pattern (console + JSON lines) gives immediate visibility during development AND machine-parseable logs for later analysis. The structured fields (trace_id, cost) are the foundation for Phase 104 (cost tracking).
