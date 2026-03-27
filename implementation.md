# Phase 101 — Unified Project Repo Restructure (Service Separation)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-27

## Goal
Create the COS monorepo with service directory structure per ADR-004. Establishes the foundational package layout for all 120 COS phases.

CLI: `python -m cos --help` / `python -m cos status` / `python -m cos info`

Outputs: Working monorepo with verified package imports

## Logic
1. Created `cos/` monorepo with 8 sub-packages (one per track A-H)
2. Added `__init__.py` with version + docstring to each package
3. Created `pyproject.toml` (PEP 621) with setuptools build backend
4. Created `cos/__main__.py` CLI with `status` and `info` subcommands
5. Created `.venv`, installed editable (`pip install -e .`)
6. Verified: CLI help, status (all 8 packages), info (ADR references), cross-imports

## Key Concepts
- **Monorepo layout**: `cos/{core,memory,reasoning,workflow,decision,interface,intelligence,autonomy}/`
- **Editable install**: `pip install -e .` enables development without reinstalling
- **`__main__.py`**: enables `python -m cos` entry point
- **pyproject.toml**: `build-backend = "setuptools.build_meta"` (not legacy backend)
- **Package per track**: imports like `from cos.core import __version__`
- **ADR compliance**: all 5 architecture decisions (ADR-001 to ADR-005) reflected in structure

## Verification Checklist
- [x] `cos/` directory with 8 sub-packages created
- [x] All `__init__.py` files present with version + docstring
- [x] `pyproject.toml` valid (fixed: `build_meta` not `_legacy`)
- [x] `pip install -e .` succeeds
- [x] `python -m cos --help` works
- [x] `python -m cos status` shows all 8 packages at v0.1.0
- [x] `from cos.core import __version__` works
- [x] Git repo initialized and pushed to Kubanjaze/cos

## Deviations from Plan
- pyproject.toml initially used `setuptools.backends._legacy:_Backend` which doesn't exist — fixed to `setuptools.build_meta`
- No `cos` vs `math.cos` naming conflict observed (Python resolves package imports before builtins)

## Risks (resolved)
- Package naming: no conflict with `math.cos` — Python package imports take precedence
- Editable install failure: fixed by correcting build backend in pyproject.toml
- Windows paths: no issues with editable install on Windows

## Results
| Metric | Value |
|--------|-------|
| Packages | 8 (core, memory, reasoning, workflow, decision, interface, intelligence, autonomy) |
| CLI commands | 3 (--help, status, info) |
| Version | 0.1.0 |
| Repo | Kubanjaze/cos |
| Cost | $0.00 |

Key finding: The monorepo skeleton is working. All 8 packages import cleanly, CLI entry point works, and editable install enables rapid development. This is the foundation for 119 more phases.
