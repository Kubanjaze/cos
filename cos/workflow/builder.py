"""COS workflow builder — programmatic workflow construction. Phase 162."""

from typing import Optional
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.builder")


class WorkflowBuilder:
    """Fluent API for building workflows."""

    def __init__(self, name: str, description: str = "", domain: str = "general"):
        self._name = name
        self._description = description
        self._domain = domain
        self._steps: list[dict] = []

    def add_step(self, name: str, command: str, subcommand: Optional[str] = None,
                 kwargs: Optional[dict] = None, condition: Optional[str] = None,
                 on_failure: str = "stop") -> "WorkflowBuilder":
        """Add a step to the workflow."""
        self._steps.append({
            "name": name, "command": command, "subcommand": subcommand,
            "kwargs": kwargs or {}, "condition": condition,
            "loop_count": 0, "on_failure": on_failure,
        })
        return self

    def add_loop_step(self, name: str, command: str, count: int,
                      kwargs: Optional[dict] = None) -> "WorkflowBuilder":
        """Add a looping step."""
        self._steps.append({
            "name": name, "command": command, "subcommand": None,
            "kwargs": kwargs or {}, "condition": None,
            "loop_count": count, "on_failure": "stop",
        })
        return self

    def build(self, investigation_id: str = "default") -> str:
        """Build and register the workflow. Returns workflow def ID."""
        from cos.workflow.schema import workflow_schema
        wid = workflow_schema.define(
            self._name, self._steps, description=self._description,
            domain=self._domain, investigation_id=investigation_id,
        )
        logger.info(f"Built workflow: {self._name} ({len(self._steps)} steps)")
        return wid

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def preview(self) -> dict:
        """Preview the workflow without saving."""
        return {
            "name": self._name, "description": self._description,
            "domain": self._domain, "steps": self._steps, "step_count": len(self._steps),
        }
