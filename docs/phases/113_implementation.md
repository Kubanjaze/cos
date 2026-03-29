# Phase 113 — Modular Plugin Architecture

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Plugin system allowing new file handlers, processors, and tools to be registered dynamically. External code can extend COS without modifying core modules.

CLI: `python -m cos plugins`

Outputs: `cos/core/plugins.py` — PluginRegistry + @register_plugin decorator

## Logic
1. `PluginRegistry` with 3 stores: file_handlers (by extension), processors (by name), tools (by name)
2. `@register_plugin("file_handler", ".xlsx")` decorator for auto-registration
3. `get_handler/get_processor/get_tool` for lookup
4. Built-in file handlers from ingestion module auto-registered on import
5. `list_plugins()` returns all by type; `total_count` property
6. CLI: `plugins` command shows all registered

## Key Concepts
- **Self-registration via decorator**: `@register_plugin(type, name)` registers at import time
- **Three plugin types**: file_handler (extension key), processor (name key), tool (name key)
- **Built-in auto-registration**: existing HANDLERS from ingestion.py registered as plugins
- **Overwrite warning**: duplicate name logs WARNING before overwriting
- **No filesystem scanning**: plugins must be explicitly imported for v0

## Verification Checklist
- [x] 5 built-in file handlers registered (.txt, .csv, .pdf, .md, .json)
- [x] `get_handler(".csv")` returns _extract_csv function
- [x] Custom @register_plugin("processor", "uppercase") works
- [x] Custom processor callable: "hello" → "HELLO"
- [x] `list_plugins()` groups by type correctly
- [x] `python -m cos plugins` CLI shows all plugins

## Risks (resolved)
- Import-time side effects: built-ins register in _register_builtins(), called once
- Name collisions: logged as WARNING before overwrite
- Discovery: explicit imports only for v0 — filesystem scanning deferred

## Results
| Metric | Value |
|--------|-------|
| Built-in plugins | 5 file handlers |
| Custom plugin test | processor/uppercase → HELLO |
| Plugin types | 3 (file_handler, processor, tool) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The decorator pattern makes plugin registration trivially easy — one line above any function. Built-in handlers from Phase 105 auto-register, proving backwards compatibility. The registry is the foundation for Phase 114 (pipeline registry).
