# Phase 114 — Pipeline Registry (List + Run Workflows)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build a pipeline registry that defines reusable multi-step workflows. A pipeline is a named sequence of COS commands executed in order. This is the foundation for Gate 2: register + run a pipeline → version outputs → show logs.

CLI: `python -m cos pipeline list` / `python -m cos pipeline run <name> [--investigation <id>]`

Outputs: Pipeline registry in `cos/core/pipelines.py`, pipeline execution logs

## Logic
1. Create `cos/core/pipelines.py` with `PipelineRegistry` class
2. Pipeline definition: `{name, steps: [{command, kwargs}], description}`
3. `register_pipeline(name, steps, description)` — adds a pipeline definition
4. `run_pipeline(name, investigation_id)` — executes steps sequentially via command registry (Phase 110)
5. Each step's output logged with investigation_id + pipeline name
6. Pipeline run creates a version stamp (Phase 109) on completion
7. Register one built-in pipeline: "ingest-and-tag" (ingest file → tag with domain)
8. CLI: `pipeline list` and `pipeline run <name>`

## Key Concepts
- **Pipeline = named sequence of registry commands**: reuses Phase 110 command registry
- **Sequential execution**: steps run in order; failure in any step stops the pipeline
- **Investigation-scoped**: all steps execute under the same investigation_id (ADR-003)
- **Version stamp on completion**: Phase 109 versioning creates audit trail
- **Gate 2 progress**: register pipeline ✅ → run pipeline → version outputs → show logs

## Verification Checklist
- [ ] Pipeline registered with name + steps
- [ ] `pipeline list` shows registered pipelines
- [ ] `pipeline run "ingest-and-tag"` executes both steps
- [ ] Steps execute via command registry (Phase 110)
- [ ] Version stamped on pipeline completion
- [ ] Pipeline failure stops at failing step

## Risks
- Command registry may not have all needed commands registered — verify at pipeline registration
- Step kwargs must match handler signatures — validated at run time
- Pipeline loops/cycles: not supported in v0 (sequential only)
