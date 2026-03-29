# Phase 114 — Pipeline Registry (List + Run Workflows)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Multi-step workflow pipelines as named sequences of command registry calls. Foundation for Gate 2: register + run pipeline → version outputs → show logs.

CLI: `python -m cos pipeline list` / `python -m cos pipeline run <name>`

Outputs: Pipeline execution results with per-step timing, version stamp on completion

## Logic
1. `PipelineRegistry` class with register/run/list_pipelines
2. Pipeline = name + steps (list of {command, kwargs, subcommand}) + description
3. `run()` executes steps sequentially via Phase 110 command registry
4. Each step logged with investigation_id; failure stops pipeline
5. Version stamp (Phase 109) created on successful completion
6. Built-in pipeline "system-check": status → config validate → storage

## Key Concepts
- **Pipeline = command sequence**: reuses Phase 110 registry.run() for each step
- **Fail-fast**: any step failure stops execution and returns partial results
- **Version stamp**: Phase 109 integration creates audit trail on completion
- **Investigation-scoped**: all steps execute under same investigation_id (ADR-003)
- **Gate 2 COMPLETE**: register ✅, run ✅, version outputs ✅, show logs ✅

## Verification Checklist
- [x] "system-check" pipeline registered (3 steps)
- [x] `pipeline list` shows name + step count + description
- [x] `pipeline run system-check` executes all 3 steps
- [x] Per-step timing: status 0.020s, config 0.001s, storage 0.012s
- [x] Version 1 stamped for inv-test on completion
- [x] Structured logging shows step progress

## Risks (resolved)
- Command not found: would raise in registry.run() — caught and logged as step failure
- Step kwargs mismatch: validated at runtime by handler signature
- No parallel steps: sequential only for v0

## Results
| Metric | Value |
|--------|-------|
| Built-in pipeline | system-check (3 steps: status, config validate, storage) |
| Execution time | 0.032s total |
| Version stamp | v1 stamped for inv-test |
| Gate 2 | ✅ COMPLETE |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Gate 2 is complete — COS can register pipelines, execute them with per-step logging, version the outputs, and show logs. The 0.032s execution for 3 steps proves the command registry overhead is negligible.
