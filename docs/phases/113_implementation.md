# Phase 113 — Modular Plugin Architecture

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build a plugin system that allows new tools, file handlers, and processors to be registered dynamically. External modules can extend COS without modifying core code. This is how the system grows from 8 packages to an ecosystem.

CLI: `python -m cos plugins list`

Outputs: Plugin registry in `cos/core/plugins.py`

## Logic
1. Create `cos/core/plugins.py` with `PluginRegistry` class
2. Plugin types: `file_handler` (new file formats), `processor` (data transformers), `tool` (CLI-accessible tools)
3. `@register_plugin(type, name)` decorator for auto-registration
4. `registry.get_handler(extension)` — find a file handler by extension
5. `registry.get_processor(name)` — find a processor by name
6. `registry.list_plugins()` — list all registered plugins by type
7. Built-in plugins: register existing file handlers (TXT, CSV, PDF) as plugins
8. CLI: `plugins list` shows all registered plugins

## Key Concepts
- **Plugin registry pattern**: plugins self-register via decorator at import time
- **Three plugin types**: file_handler (by extension), processor (by name), tool (by name)
- **Decorator-based registration**: `@register_plugin("file_handler", ".xlsx")` on a function
- **Discovery**: import a module → its decorated functions auto-register
- **Extensibility**: third-party code can add plugins by decorating functions and importing

## Verification Checklist
- [ ] Built-in file handlers (TXT, CSV, PDF) registered as plugins
- [ ] `@register_plugin` decorator works for new handlers
- [ ] `registry.get_handler(".csv")` returns the CSV handler
- [ ] `registry.list_plugins()` shows all by type
- [ ] `python -m cos plugins list` CLI works
- [ ] Custom plugin registration verified

## Risks
- Import-time side effects: plugins register on import — order may matter
- Name collisions: later registration overwrites earlier — log a warning
- Plugin discovery: for v0, plugins must be explicitly imported (no filesystem scanning)
