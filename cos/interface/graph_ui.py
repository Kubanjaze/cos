"""COS graph visualization UI — interactive graph views. Phase 199.

Also covers: Phase 202 (workflow builder UI).
"""

import json
import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.graph_ui")


class GraphUI:
    """Text-based graph visualization interface."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def render_entity_graph(self, entity_name: str, depth: int = 1) -> str:
        """Render an entity's neighborhood as ASCII."""
        from cos.memory.visualization import memory_viz
        return memory_viz.graph_ascii(entity_name, depth=depth)

    def render_domain_map(self) -> str:
        """Render domain structure."""
        from cos.memory.visualization import memory_viz
        clusters = memory_viz.domain_clusters()
        lines = ["Domain Map:"]
        for domain, concepts in clusters.items():
            lines.append(f"\n  [{domain}] ({len(concepts)} concepts)")
            for c in concepts[:5]:
                bar = "█" * int(c["confidence"] * 10)
                lines.append(f"    {c['name']:>20} {bar} {c['confidence']:.0%}")
        return "\n".join(lines)

    def render_decision_tree(self) -> str:
        """Render decision tree visualization."""
        conn = sqlite3.connect(self._db_path)
        decisions = conn.execute(
            "SELECT id, title, confidence, status FROM decisions ORDER BY confidence DESC"
        ).fetchall()
        conn.close()

        if not decisions:
            return "No decisions to visualize."

        lines = ["Decision Tree:"]
        for did, title, conf, status in decisions:
            icon = "✓" if "outcome" in status else "?" if status == "proposed" else "○"
            bar = "█" * int(conf * 10)
            lines.append(f"  {icon} {title[:35]:>35} {bar} {conf:.0%} [{status}]")
        return "\n".join(lines)

    def export_for_web(self) -> str:
        """Export graph data as JSON for potential web UI."""
        from cos.memory.visualization import memory_viz
        return memory_viz.export_graph(format="json")

    def stats(self) -> dict:
        return {"views": ["entity_graph", "domain_map", "decision_tree"], "format": "text+json"}


# Phase 202: Workflow builder UI
class WorkflowBuilderUI:
    """Text-based workflow builder interface."""

    def interactive_build(self, name: str) -> str:
        """Show available steps for building a workflow."""
        from cos.workflow.templates import template_registry
        templates = template_registry.list_templates()

        lines = [f"Workflow Builder: {name}", "=" * 40, "", "Available templates:"]
        for t in templates:
            lines.append(f"  {t['name']:>20} ({t['steps']} steps) — {t['description']}")

        lines.append("\nAvailable commands:")
        from cos.core.cli_registry import registry
        for cmd in sorted(registry._commands.keys()):
            lines.append(f"  {cmd}")

        lines.append(f"\nUse: python -m cos wf define \"{name}\" '<steps_json>'")
        return "\n".join(lines)

    def stats(self) -> dict:
        from cos.workflow.templates import template_registry
        return template_registry.stats()


graph_ui = GraphUI()
workflow_builder_ui = WorkflowBuilderUI()
