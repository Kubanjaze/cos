# Phase 117 — Batch Execution Engine

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build a batch execution engine that processes multiple items (files, compounds, queries) through a pipeline efficiently. Supports progress tracking, error collection, and summary reporting.

CLI: `python -m cos batch ingest <dir_or_glob> [--investigation <id>]`

Outputs: Batch results summary, per-item status in `cos/core/batch.py`

## Logic
1. Create `cos/core/batch.py` with `BatchExecutor` class
2. `run_batch(items, operation, investigation_id)` — processes items sequentially with progress
3. Progress callback: emits "batch.progress" events via Phase 116 event bus
4. Error collection: failed items recorded but don't stop batch (configurable)
5. Summary: total, succeeded, failed, duration, items per second
6. CLI: `batch ingest <dir>` — ingest all supported files in a directory
7. Integration: uses Phase 105 ingestion for file processing

## Key Concepts
- **Batch = operation applied to many items**: files, SMILES, queries, etc.
- **Fail-continue mode**: failed items logged but batch continues (vs fail-fast)
- **Progress events**: "batch.progress" emitted via event bus (Phase 116)
- **Summary stats**: total/succeeded/failed/duration/rate
- **Generic executor**: operation is a callable, items are any iterable

## Verification Checklist
- [ ] Batch processes multiple items with progress
- [ ] Failed items don't stop batch (fail-continue mode)
- [ ] Summary shows total/succeeded/failed/duration
- [ ] `batch ingest <dir>` CLI ingests all files
- [ ] Events emitted for progress updates

## Risks
- Large batches may run long — progress reporting mitigates
- Memory: items processed one at a time, no bulk loading
- Error accumulation: large error lists — cap at 100 error details
