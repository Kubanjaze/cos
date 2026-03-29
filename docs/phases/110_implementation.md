# Phase 110 — CLI → Service Transition (Pipelines as APIs)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Refactor COS commands into a command registry so every CLI command is also callable programmatically. Bridge between "scripts you run" and "services you call" (ADR-001).

CLI: `python -m cos --help` (all existing commands, now also via `registry.run()`)

Outputs: `registry` singleton via `from cos.core.cli_registry import registry`

## Logic
1. `CommandRegistry` class with `register()`, `register_sub()`, `run()`, `list_commands()`
2. Each handler is a plain Python function with keyword args
3. `run()` captures stdout and returns as string — enables programmatic use
4. All 7 existing command groups registered: info, status, config, cost, storage, ingest, artifacts
5. Subcommands via `register_sub("config", "show", handler)` pattern
6. `__main__.py` continues to use argparse for CLI — registry is the programmatic layer alongside it

## Key Concepts
- **Command registry pattern**: functions registered by name, introspectable via `list_commands()`
- **Dual invocation**: same handler callable from CLI (argparse) or code (`registry.run()`)
- **stdout capture**: `registry.run()` redirects stdout to StringIO, returns output as string
- **ADR-001 bridge**: each handler could become a FastAPI endpoint — just wrap `registry.run(name, kwargs)`
- **No breaking changes**: all existing CLI behavior preserved

## Verification Checklist
- [x] All 11 CLI commands still work (config show/validate, cost summary/reset, ingest, artifacts, tag, search, task *, storage, version list, status, info)
- [x] `registry.list_commands()` returns 7 registered command groups
- [x] `registry.run("info", {})` returns COS info text programmatically
- [x] `registry.run("config", subcommand="validate")` works
- [x] `registry.run("storage")` returns storage info text
- [x] No behavior regression from current CLI

## Risks (resolved)
- argparse/registry argument mismatch: handlers use **kwargs, argparse passes parsed attrs — coexist cleanly
- stdout capture side effects: uses StringIO redirect, restored in finally block
- Over-engineering: kept registry to 4 methods (register, register_sub, run, list_commands)

## Results
| Metric | Value |
|--------|-------|
| Commands registered | 7 groups (info, status, config, cost, storage, ingest, artifacts) |
| Subcommands | 4 (config show/validate, cost summary/reset) |
| Programmatic invocation | Verified for info, config validate, storage |
| CLI regression | None — all 11 commands pass |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The registry pattern gives us programmatic command invocation for free. `registry.run("ingest", {"file": "data.csv"})` works identically to `python -m cos ingest data.csv`. This is the foundation for workflow execution (Phase 163) where pipelines chain registry commands.
