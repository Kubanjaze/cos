"""COS pipeline registry — named multi-step workflows.

Defines reusable pipelines as sequences of command registry calls.

Usage:
    from cos.core.pipelines import pipeline_registry
    pipeline_registry.register("my-pipeline", [
        {"command": "ingest", "kwargs": {"file": "data.csv"}},
        {"command": "info"},
    ], description="Ingest then show info")
    pipeline_registry.run("my-pipeline", investigation_id="inv-001")
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from cos.core.logging import get_logger

logger = get_logger("cos.core.pipelines")


@dataclass
class PipelineStep:
    command: str
    kwargs: dict = field(default_factory=dict)
    subcommand: Optional[str] = None


@dataclass
class Pipeline:
    name: str
    steps: list[PipelineStep]
    description: str = ""


class PipelineRegistry:
    """Registry of named multi-step workflows."""

    def __init__(self):
        self._pipelines: dict[str, Pipeline] = {}

    def register(
        self,
        name: str,
        steps: list[dict],
        description: str = "",
    ) -> None:
        """Register a pipeline. Each step is {command, kwargs?, subcommand?}."""
        parsed_steps = [
            PipelineStep(
                command=s["command"],
                kwargs=s.get("kwargs", {}),
                subcommand=s.get("subcommand"),
            )
            for s in steps
        ]
        self._pipelines[name] = Pipeline(name=name, steps=parsed_steps, description=description)
        logger.info(f"Pipeline registered: '{name}' ({len(parsed_steps)} steps)")

    def run(self, name: str, investigation_id: str = "default") -> dict:
        """Execute a pipeline. Returns results dict."""
        from cos.core.cli_registry import registry
        from cos.core.versioning import version_manager

        if name not in self._pipelines:
            raise ValueError(f"Pipeline not found: {name}")

        pipeline = self._pipelines[name]
        logger.info(
            f"Running pipeline '{name}' ({len(pipeline.steps)} steps)",
            extra={"investigation_id": investigation_id},
        )

        results = {"pipeline": name, "investigation_id": investigation_id, "steps": [], "status": "running"}
        start = time.time()

        for i, step in enumerate(pipeline.steps):
            step_start = time.time()
            logger.info(
                f"Step {i+1}/{len(pipeline.steps)}: {step.command}" +
                (f" {step.subcommand}" if step.subcommand else ""),
                extra={"investigation_id": investigation_id},
            )

            try:
                output = registry.run(step.command, step.kwargs, subcommand=step.subcommand)
                step_result = {
                    "step": i + 1,
                    "command": step.command,
                    "subcommand": step.subcommand,
                    "status": "completed",
                    "output": output.strip() if output else "",
                    "duration_s": round(time.time() - step_start, 3),
                }
            except Exception as e:
                step_result = {
                    "step": i + 1,
                    "command": step.command,
                    "status": "failed",
                    "error": str(e),
                    "duration_s": round(time.time() - step_start, 3),
                }
                results["steps"].append(step_result)
                results["status"] = "failed"
                logger.error(f"Pipeline '{name}' failed at step {i+1}: {e}")
                return results

            results["steps"].append(step_result)

        results["status"] = "completed"
        results["total_duration_s"] = round(time.time() - start, 3)

        # Version stamp on completion
        version_manager.stamp(investigation_id, description=f"Pipeline '{name}' completed")

        logger.info(
            f"Pipeline '{name}' completed in {results['total_duration_s']:.3f}s",
            extra={"investigation_id": investigation_id},
        )
        return results

    def list_pipelines(self) -> list[dict]:
        """List all registered pipelines."""
        return [
            {"name": p.name, "steps": len(p.steps), "description": p.description}
            for p in self._pipelines.values()
        ]


# Singleton
pipeline_registry = PipelineRegistry()

# Register built-in pipeline
pipeline_registry.register(
    "system-check",
    [
        {"command": "status"},
        {"command": "config", "subcommand": "validate"},
        {"command": "storage"},
    ],
    description="Run system status, config validation, and storage check",
)
