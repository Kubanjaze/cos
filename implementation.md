# Phase 101 — Unified Project Repo Restructure (Service Separation)

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-27

## Goal
Create the COS monorepo with service directory structure. Establish the foundational package layout that all subsequent COS phases will build into. This is the skeleton — no business logic yet, just structure + imports + a working CLI entry point.

CLI: `python -m cos --help`

Outputs: Working monorepo with package imports verified

## Logic
1. Create `cos/` monorepo at `C:\Users\Kerwyn\PycharmProjects\cos\`
2. Create package directories per ADR-004: `cos/core/`, `cos/memory/`, `cos/reasoning/`, `cos/workflow/`, `cos/decision/`, `cos/interface/`, `cos/intelligence/`, `cos/autonomy/`
3. Add `__init__.py` to each package with version + docstring
4. Create `pyproject.toml` with package metadata + dependencies
5. Create `cos/__main__.py` as CLI entry point (`python -m cos`)
6. Create `.venv`, install in editable mode (`pip install -e .`)
7. Verify: `python -m cos --help` works, cross-package imports work

## Key Concepts
- **Monorepo**: single repo `Kubanjaze/cos` containing all COS code
- **Package per track**: each track (A-H) maps to a top-level package under `cos/`
- **Editable install**: `pip install -e .` allows development without reinstalling
- **`__main__.py`**: enables `python -m cos` CLI entry point
- **pyproject.toml**: modern Python packaging (PEP 621), replaces setup.py
- **ADR-004 compliance**: monorepo with service directories

## Verification Checklist
- [ ] `cos/` directory with 8 sub-packages created
- [ ] All `__init__.py` files present
- [ ] `pyproject.toml` valid
- [ ] `pip install -e .` succeeds
- [ ] `python -m cos --help` works
- [ ] `from cos.core import __version__` works from Python
- [ ] Git repo initialized and pushed to Kubanjaze/cos

## Risks
- Package naming conflict: `cos` may conflict with math.cos — verify no import collision
- Windows path issues with editable installs — test thoroughly
- pyproject.toml syntax must be correct for build system
