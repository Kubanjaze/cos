"""COS command registry — bridges CLI and programmatic invocation.

Every COS command is a registered handler function callable from CLI or Python code.

Usage:
    from cos.core.cli_registry import registry
    registry.run("info", {})  # programmatic
    registry.list_commands()  # introspection
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from cos.core.logging import get_logger

logger = get_logger("cos.core.cli_registry")


@dataclass
class Command:
    name: str
    handler: Callable
    description: str = ""
    subcommands: dict[str, "Command"] = field(default_factory=dict)


class CommandRegistry:
    """Registry of COS commands — callable from CLI or code."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a top-level command."""
        self._commands[name] = Command(name=name, handler=handler, description=description)

    def register_sub(
        self,
        parent: str,
        name: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a subcommand under a parent."""
        if parent not in self._commands:
            self._commands[parent] = Command(name=parent, handler=lambda **kw: None, description="")
        self._commands[parent].subcommands[name] = Command(name=name, handler=handler, description=description)

    def run(self, command: str, kwargs: Optional[dict] = None, subcommand: Optional[str] = None) -> str:
        """Run a command programmatically. Returns output as string."""
        import io
        import sys

        if command not in self._commands:
            return f"Unknown command: {command}"

        cmd = self._commands[command]

        # If subcommand specified, dispatch to it
        if subcommand:
            if subcommand not in cmd.subcommands:
                return f"Unknown subcommand: {command} {subcommand}"
            handler = cmd.subcommands[subcommand].handler
        else:
            handler = cmd.handler

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()
        try:
            handler(**(kwargs or {}))
            return captured.getvalue()
        except Exception as e:
            return f"Error: {e}"
        finally:
            sys.stdout = old_stdout

    def list_commands(self) -> list[dict]:
        """List all registered commands."""
        result = []
        for name, cmd in sorted(self._commands.items()):
            entry = {"name": name, "description": cmd.description}
            if cmd.subcommands:
                entry["subcommands"] = [
                    {"name": s.name, "description": s.description}
                    for s in cmd.subcommands.values()
                ]
            result.append(entry)
        return result


# Singleton
registry = CommandRegistry()


# ── Register all COS command handlers ───────────────────────────────────

def _register_all():
    """Register all built-in COS commands."""
    from cos import __version__

    # info
    def cmd_info():
        print(f"COS — Cognitive Operating System v{__version__}")
        print("Tracks: A (Core), B (Memory), C (Reasoning), D (Workflow),")
        print("        E (Decision), F (Interface), G (Intelligence), H (Autonomy)")
        print("Build: Monorepo with service directories (ADR-004)")
        print("Storage: SQLite + filesystem (ADR-002)")
        print("Unit of work: Investigation (ADR-003)")
    registry.register("info", cmd_info, "Show package info")

    # status
    def cmd_status():
        print(f"COS v{__version__}")
        print("Packages:")
        for pkg in ["core", "memory", "reasoning", "workflow", "decision", "interface", "intelligence", "autonomy"]:
            try:
                mod = __import__(f"cos.{pkg}", fromlist=[pkg])
                print(f"  cos.{pkg}: v{mod.__version__}")
            except ImportError as e:
                print(f"  cos.{pkg}: MISSING ({e})")
    registry.register("status", cmd_status, "Show system status")

    # config show
    def cmd_config_show():
        from cos.core.config import settings
        print(settings.show())
    registry.register_sub("config", "show", cmd_config_show, "Show current configuration")

    # config validate
    def cmd_config_validate():
        from cos.core.config import settings
        errors = settings.validate()
        if errors:
            print("Configuration errors:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("Configuration valid.")
    registry.register_sub("config", "validate", cmd_config_validate, "Validate configuration")

    # cost summary
    def cmd_cost_summary():
        from cos.core.cost import cost_tracker
        s = cost_tracker.get_summary()
        print(f"COS Cost Summary\n{'='*45}")
        print(f"Total cost:   ${s['total_cost']:.4f}")
        print(f"Total events: {s['total_events']}")
        if s["by_model"]:
            print(f"\nBy model:")
            for m in s["by_model"]:
                print(f"  {m['model']:35s} {m['events']:3d} calls  ${m['cost']:.4f}")
        if s["by_investigation"]:
            print(f"\nBy investigation:")
            for inv in s["by_investigation"]:
                print(f"  {inv['investigation_id']:35s} {inv['events']:3d} calls  ${inv['cost']:.4f}")
    registry.register_sub("cost", "summary", cmd_cost_summary, "Show cost summary")

    # cost reset
    def cmd_cost_reset():
        from cos.core.cost import cost_tracker
        cost_tracker.reset()
        print("Cost events cleared.")
    registry.register_sub("cost", "reset", cmd_cost_reset, "Clear all cost events")

    # storage
    def cmd_storage():
        from cos.core.storage import storage
        info = storage.info()
        print(f"COS Storage Info\n{'='*45}")
        print(f"Files:\n  Backend:  {info['file_backend']}\n  Base dir: {info['file_base']}")
        print(f"  Files:    {info['file_count']}\n  Size:     {info['file_size_bytes']:,} bytes")
        print(f"\nDatabase:\n  Backend:  {info['db_backend']}\n  Path:     {info['db_path']}")
        print(f"  Size:     {info['db_size_bytes']:,} bytes\n  Tables:   {', '.join(info['db_tables'])}")
    registry.register("storage", cmd_storage, "Show storage backend info")

    # ingest
    def cmd_ingest(file: str = "", investigation: str = "default"):
        from cos.core.ingestion import ingest_file
        artifact = ingest_file(file, investigation_id=investigation)
        print(f"Ingested: {artifact.uri}")
        print(f"  ID:     {artifact.id}\n  Type:   {artifact.type}")
        print(f"  Hash:   {artifact.hash[:16]}...\n  Size:   {artifact.size_bytes} bytes")
    registry.register("ingest", cmd_ingest, "Ingest a file into COS")

    # artifacts
    def cmd_artifacts(investigation: str = None):
        from cos.core.ingestion import list_artifacts
        artifacts = list_artifacts(investigation)
        if not artifacts:
            print("No artifacts found.")
        else:
            print(f"{'ID':>8} {'Type':>4} {'Size':>8} {'Investigation':>15} {'Hash':>14} Created")
            for a in artifacts:
                print(f"{a['id'][:8]:>8} {a['type']:>4} {a['size_bytes']:>8} {a['investigation_id']:>15} {a['hash']:>14} {a['created_at']}")
    registry.register("artifacts", cmd_artifacts, "List ingested artifacts")


_register_all()
