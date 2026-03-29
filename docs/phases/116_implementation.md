# Phase 116 — Event System (Trigger-Based Execution)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Build an event system that allows COS components to emit events and register listeners that react to them. Events like "artifact_ingested", "investigation_created", "pipeline_completed" can trigger follow-up actions without tight coupling between modules.

CLI: `python -m cos events list` (show registered event types + listeners)

Outputs: Event bus in `cos/core/events.py`

## Logic
1. Create `cos/core/events.py` with `EventBus` class
2. `emit(event_type, payload)` — fires an event to all registered listeners
3. `on(event_type, callback)` — registers a listener for an event type
4. `off(event_type, callback)` — unregisters a listener
5. Event types: strings like "artifact.ingested", "investigation.created", "pipeline.completed"
6. Payloads: dicts with event-specific data (artifact_id, investigation_id, etc.)
7. All events logged with structured fields (Phase 103)
8. Synchronous dispatch for v0 (listeners called inline)

## Key Concepts
- **Publish-subscribe pattern**: emitters don't know about listeners, loose coupling
- **Event types as dotted strings**: "artifact.ingested", "cost.warning", "pipeline.step.completed"
- **Synchronous dispatch**: listeners called in registration order, inline (no async for v0)
- **Structured logging**: every event emission logged with type + payload summary
- **Integration hooks**: Phase 105 ingestion could emit "artifact.ingested" → Phase 106 auto-tag

## Verification Checklist
- [ ] `on("test.event", callback)` registers listener
- [ ] `emit("test.event", {"key": "value"})` triggers callback with payload
- [ ] Multiple listeners on same event all fire
- [ ] `off()` unregisters listener
- [ ] Events logged with structured fields
- [ ] `python -m cos events list` shows registered types

## Risks
- Listener exceptions could break event chain — wrap each listener in try/except
- Event storms: one event triggering another that triggers the first — no cycle detection in v0
- Memory leaks: listeners hold references — acceptable for local-first single-process (ADR-001)
