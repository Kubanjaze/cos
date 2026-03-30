"""COS workflow templates — reusable workflow patterns. Phase 170."""

from typing import Optional
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.templates")


# Built-in templates
TEMPLATES = {
    "ingest-analyze": {
        "description": "Ingest a file, store as document, extract entities, extract relations",
        "steps": [
            {"name": "ingest", "command": "status", "kwargs": {}},
            {"name": "check-entities", "command": "entities", "subcommand": "stats", "kwargs": {}},
            {"name": "check-relations", "command": "relations", "subcommand": "stats", "kwargs": {}},
        ],
    },
    "health-check": {
        "description": "System health check workflow",
        "steps": [
            {"name": "status", "command": "status", "kwargs": {}},
            {"name": "config-validate", "command": "config", "subcommand": "validate", "kwargs": {}},
            {"name": "storage", "command": "storage", "kwargs": {}},
            {"name": "health", "command": "health", "kwargs": {}},
        ],
    },
    "knowledge-audit": {
        "description": "Audit knowledge quality: gaps, conflicts, scores",
        "steps": [
            {"name": "check-gaps", "command": "gaps", "subcommand": "summary", "kwargs": {}},
            {"name": "scan-conflicts", "command": "conflicts", "subcommand": "scan", "kwargs": {}},
            {"name": "score-entities", "command": "scores", "subcommand": "score-all", "kwargs": {"target_type": "entity"}},
        ],
    },
}


class TemplateRegistry:
    """Manages workflow templates."""

    def __init__(self):
        self._templates = dict(TEMPLATES)

    def list_templates(self) -> list[dict]:
        return [{"name": name, "description": t["description"], "steps": len(t["steps"])}
                for name, t in self._templates.items()]

    def get(self, name: str) -> Optional[dict]:
        return self._templates.get(name)

    def instantiate(self, template_name: str, workflow_name: Optional[str] = None,
                    investigation_id: str = "default") -> str:
        """Create a workflow from a template. Returns workflow def ID."""
        template = self.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        from cos.workflow.schema import workflow_schema
        wf_name = workflow_name or f"{template_name}-instance"
        wid = workflow_schema.define(
            wf_name, template["steps"], description=f"From template: {template_name}",
            investigation_id=investigation_id,
        )
        logger.info(f"Instantiated template '{template_name}' as '{wf_name}'")
        return wid

    def register(self, name: str, description: str, steps: list[dict]):
        """Register a custom template."""
        self._templates[name] = {"description": description, "steps": steps}

    def stats(self) -> dict:
        return {"total_templates": len(self._templates), "builtin": len(TEMPLATES)}


template_registry = TemplateRegistry()
