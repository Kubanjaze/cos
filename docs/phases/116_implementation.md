# Phase 116 — Event System (Trigger-Based Execution)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Publish-subscribe event bus for loose coupling between COS components. Events like "artifact.ingested" can trigger follow-up actions without tight coupling.

CLI: `python -m cos events`

Outputs: `cos/core/events.py` — EventBus singleton

## Logic
1. `EventBus` class: `on(type, callback)`, `off(type, callback)`, `emit(type, payload)`
2. Synchronous dispatch: listeners called inline in registration order
3. Error isolation: each listener wrapped in try/except — failure doesn't break chain
4. Structured logging on every emit + register/unregister
5. `list_events()` returns type → listener count map
6. `total_emits` and `total_listeners` properties for stats

## Key Concepts
- **Pub-sub pattern**: emitters don't know about listeners, decoupled modules
- **Dotted event types**: "artifact.ingested", "pipeline.completed", "cost.warning"
- **Error isolation**: bad listeners caught and logged, don't break other listeners
- **Synchronous for v0**: no async — acceptable for local-first (ADR-001)
- **Foundation for Phase 168**: event-triggered workflows will use this bus

## Verification Checklist
- [x] `on()` registers listener, confirmed via emit callback
- [x] `emit()` fires to all registered listeners (2 listeners both called)
- [x] `off()` removes listener (1 listener remaining after removal)
- [x] Error in listener caught — doesn't break event chain
- [x] `list_events()` returns correct type → count mapping
- [x] CLI shows registered events (empty at startup — listeners register at runtime)

## Risks (resolved)
- Listener exceptions: wrapped in try/except per listener
- Event storms/cycles: no detection in v0 — acceptable for current module count
- Memory leaks from listener references: acceptable for single-process (ADR-001)

## Results
| Metric | Value |
|--------|-------|
| Tests | 5/5 (register, emit, multi, off, error handling) |
| Total emits in test | 4 |
| Error handling | Listener ValueError caught, logged, didn't break chain |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Error isolation per listener is critical — one bad listener must not break the event chain. The try/except per callback ensures system resilience. This event bus is the foundation for reactive workflows (Phase 168).
