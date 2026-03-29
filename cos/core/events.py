"""COS event system — publish-subscribe for loose coupling.

Components emit events, listeners react without tight coupling.

Usage:
    from cos.core.events import event_bus

    def on_ingest(payload):
        print(f"Artifact ingested: {payload['artifact_id']}")

    event_bus.on("artifact.ingested", on_ingest)
    event_bus.emit("artifact.ingested", {"artifact_id": "abc-123"})
"""

from typing import Callable

from cos.core.logging import get_logger

logger = get_logger("cos.core.events")


class EventBus:
    """Synchronous publish-subscribe event bus."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}
        self._emit_count: int = 0

    def on(self, event_type: str, callback: Callable) -> None:
        """Register a listener for an event type."""
        self._listeners.setdefault(event_type, []).append(callback)
        logger.info(f"Listener registered: {event_type} → {callback.__name__}")

    def off(self, event_type: str, callback: Callable) -> bool:
        """Unregister a listener. Returns True if removed."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                logger.info(f"Listener removed: {event_type} → {callback.__name__}")
                return True
            except ValueError:
                pass
        return False

    def emit(self, event_type: str, payload: dict = None) -> int:
        """Emit an event to all registered listeners. Returns number of listeners called."""
        payload = payload or {}
        listeners = self._listeners.get(event_type, [])
        self._emit_count += 1

        if not listeners:
            logger.debug(f"Event '{event_type}' emitted (no listeners)")
            return 0

        logger.info(
            f"Event '{event_type}' → {len(listeners)} listener(s)",
            extra={"investigation_id": payload.get("investigation_id", "")},
        )

        called = 0
        for listener in listeners:
            try:
                listener(payload)
                called += 1
            except Exception as e:
                logger.error(f"Listener {listener.__name__} failed on '{event_type}': {e}")

        return called

    def list_events(self) -> dict[str, int]:
        """List registered event types with listener counts."""
        return {etype: len(listeners) for etype, listeners in sorted(self._listeners.items())}

    @property
    def total_emits(self) -> int:
        return self._emit_count

    @property
    def total_listeners(self) -> int:
        return sum(len(v) for v in self._listeners.values())


# Singleton
event_bus = EventBus()
