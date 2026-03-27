# Phase 102 — Central Config System (Env + Runtime Configs)

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-27

## Goal
Build a unified configuration system for COS. All modules read from one `settings` singleton — no scattered `os.getenv()` calls. Layered loading: defaults → cos.toml → .env → environment variables.

CLI: `python -m cos config show` / `python -m cos config validate`

Outputs: `settings` singleton accessible via `from cos.core.config import settings`

## Logic
1. `Settings` dataclass in `cos/core/config.py` with typed fields + defaults
2. `load_settings()` applies layered precedence: defaults → TOML → .env → env vars
3. `.env` loader: simple key=value parser, strips quotes
4. TOML loader: uses stdlib `tomllib` (Python 3.11+), fallback to `tomli`
5. Env vars with `COS_` prefix map to settings (e.g., `COS_LOG_LEVEL=DEBUG`)
6. `ANTHROPIC_API_KEY` picked up directly (no prefix needed)
7. Singleton: `settings = load_settings()` at module level
8. CLI subcommands `config show` and `config validate` added to `__main__.py`

## Key Concepts
- **Layered config**: defaults → file → env (last wins) — standard 12-factor pattern
- **Dataclass (not Pydantic)**: zero external deps, stdlib only for core config
- **Singleton pattern**: `settings` loaded once at import, used everywhere
- **COS_ prefix**: env vars like `COS_STORAGE_DIR`, `COS_LOG_LEVEL` map automatically
- **Validation**: `settings.validate()` returns list of errors (empty = valid)
- **ADR compliance**: storage_dir defaults to `~/.cos/`, eval weights match ADR-005 (40/40/20)

## Verification Checklist
- [x] `Settings` model loads defaults (storage_dir=~/.cos, db_name=cos.db)
- [x] Environment variables override defaults (COS_ prefix)
- [x] .env file loading works (key=value parser)
- [x] `python -m cos config show` prints all settings with masked API key
- [x] `python -m cos config validate` returns valid
- [x] `from cos.core.config import settings` works — singleton importable

## Risks (resolved)
- Pydantic dependency avoided — used stdlib dataclass instead (zero deps for core)
- Circular imports: config has no COS module imports — safe as leaf dependency
- TOML loading: tomllib is stdlib in Python 3.11+ — no issue with Python 3.13

## Results
| Metric | Value |
|--------|-------|
| Config fields | 11 (storage, API, logging, cost, evaluation) |
| Load layers | 3 (TOML → .env → env vars) |
| CLI commands | 2 (config show, config validate) |
| External deps | 0 (stdlib only) |
| Cost | $0.00 |

Key finding: Using a stdlib dataclass instead of Pydantic Settings keeps the core dependency-free. The layered loading pattern (defaults → file → env) is production-standard and sufficient for local-first COS.
