# Phase 117 — Batch Execution Engine

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Generic batch processor that applies an operation to many items with progress tracking, error collection, and summary reporting. Integrates with event bus for progress events.

CLI: `python -m cos batch ingest <dir>` | Programmatic: `batch_executor.run(items, operation)`

Outputs: `BatchResult` dataclass with total/succeeded/failed/duration/rate/errors

## Logic
1. `BatchExecutor.run(items, operation, investigation_id, fail_fast=False)`
2. Iterates items, calls operation on each, catches exceptions per item
3. Progress events emitted via event bus every 10% (or every item for small batches)
4. Errors collected (capped at 100 details) — batch continues unless fail_fast=True
5. Summary: BatchResult with success_rate property
6. CLI: `batch ingest <dir>` finds supported files and ingests all

## Key Concepts
- **Fail-continue**: default mode — failed items don't stop batch
- **Progress events**: "batch.progress" emitted via Phase 116 event bus
- **Error cap**: MAX_ERROR_DETAILS=100 prevents unbounded error collection
- **Generic**: operation is any callable, items are any iterable
- **BatchResult dataclass**: typed result with success_rate property

## Verification Checklist
- [x] Batch processes 5 items, 4 succeed, 1 fails (division by zero)
- [x] Failed item doesn't stop batch (fail-continue mode)
- [x] Summary: 80% success rate, 0.001s duration, 5000 items/s
- [x] Error details captured: item=0, error="division by zero", index=3
- [x] Event bus integration (batch.progress + batch.completed emitted)

## Risks (resolved)
- Large batches: progress events every 10% keeps output manageable
- Error accumulation: capped at 100 details
- Memory: items processed one at a time, no bulk loading

## Results
| Metric | Value |
|--------|-------|
| Test batch | 5 items, 4/5 succeeded (80%) |
| Duration | 0.001s |
| Rate | 5000.0 items/s |
| Error captured | item=0, division by zero, index=3 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The fail-continue pattern is essential for batch operations — one bad item shouldn't waste the work done on all others. Error collection with capping prevents unbounded memory growth on large batches.
