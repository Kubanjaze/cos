"""COS modular plugin architecture.

Allows new file handlers, processors, and tools to be registered dynamically.
Plugins self-register via decorator at import time.

Usage:
    from cos.core.plugins import plugin_registry, register_plugin

    @register_plugin("file_handler", ".xlsx")
    def handle_xlsx(path: str) -> str:
        ...  # return extracted text

    handler = plugin_registry.get_handler(".xlsx")
"""

from typing import Callable, Optional

from cos.core.logging import get_logger

logger = get_logger("cos.core.plugins")


class PluginRegistry:
    """Central registry for COS plugins."""

    def __init__(self):
        self._file_handlers: dict[str, Callable] = {}
        self._processors: dict[str, Callable] = {}
        self._tools: dict[str, Callable] = {}

    def register(self, plugin_type: str, name: str, fn: Callable) -> None:
        """Register a plugin by type and name."""
        store = self._get_store(plugin_type)
        if name in store:
            logger.warning(f"Plugin '{name}' ({plugin_type}) being overwritten")
        store[name] = fn
        logger.info(f"Plugin registered: {plugin_type}/{name}")

    def _get_store(self, plugin_type: str) -> dict:
        stores = {
            "file_handler": self._file_handlers,
            "processor": self._processors,
            "tool": self._tools,
        }
        if plugin_type not in stores:
            raise ValueError(f"Unknown plugin type: {plugin_type}. Valid: {list(stores.keys())}")
        return stores[plugin_type]

    def get_handler(self, extension: str) -> Optional[Callable]:
        """Get a file handler by extension (e.g., '.csv')."""
        return self._file_handlers.get(extension)

    def get_processor(self, name: str) -> Optional[Callable]:
        """Get a processor by name."""
        return self._processors.get(name)

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_plugins(self) -> dict[str, list[str]]:
        """List all registered plugins grouped by type."""
        return {
            "file_handler": sorted(self._file_handlers.keys()),
            "processor": sorted(self._processors.keys()),
            "tool": sorted(self._tools.keys()),
        }

    @property
    def total_count(self) -> int:
        return len(self._file_handlers) + len(self._processors) + len(self._tools)


# Singleton
plugin_registry = PluginRegistry()


def register_plugin(plugin_type: str, name: str) -> Callable:
    """Decorator to register a function as a COS plugin.

    Usage:
        @register_plugin("file_handler", ".xlsx")
        def handle_xlsx(path): ...
    """
    def decorator(fn: Callable) -> Callable:
        plugin_registry.register(plugin_type, name, fn)
        return fn
    return decorator


# ── Register built-in file handlers as plugins ─────────────────────────

def _register_builtins():
    """Register built-in file handlers from cos.core.ingestion."""
    try:
        from cos.core.ingestion import HANDLERS
        for ext, handler in HANDLERS.items():
            plugin_registry.register("file_handler", ext, handler)
    except ImportError:
        pass

_register_builtins()
