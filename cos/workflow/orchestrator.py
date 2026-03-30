"""COS multi-workflow orchestrator — coordinate multiple workflows. Phase 169."""

import time
from typing import Optional
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.orchestrator")


class WorkflowOrchestrator:
    """Coordinates execution of multiple workflows."""

    def run_sequence(self, workflow_names: list[str], investigation_id: str = "default") -> dict:
        """Run workflows in sequence."""
        from cos.workflow.executor import workflow_executor
        results = []
        start = time.time()
        overall_status = "completed"

        for name in workflow_names:
            try:
                result = workflow_executor.execute(name, investigation_id=investigation_id)
                results.append({"workflow": name, "status": result["status"], "duration_s": result["duration_s"]})
                if result["status"] == "failed":
                    overall_status = "failed"
                    break
            except Exception as e:
                results.append({"workflow": name, "status": "error", "error": str(e)[:100]})
                overall_status = "failed"
                break

        return {
            "mode": "sequence", "workflows": results, "status": overall_status,
            "total_duration_s": round(time.time() - start, 3),
        }

    def run_parallel(self, workflow_names: list[str], investigation_id: str = "default") -> dict:
        """Run workflows sequentially (true parallel requires threading — deferred)."""
        # Sequential execution with parallel semantics (fail-independent)
        from cos.workflow.executor import workflow_executor
        results = []
        start = time.time()

        for name in workflow_names:
            try:
                result = workflow_executor.execute(name, investigation_id=investigation_id)
                results.append({"workflow": name, "status": result["status"], "duration_s": result["duration_s"]})
            except Exception as e:
                results.append({"workflow": name, "status": "error", "error": str(e)[:100]})

        failed = sum(1 for r in results if r["status"] != "completed")
        return {
            "mode": "parallel", "workflows": results,
            "status": "completed" if failed == 0 else "partial",
            "total_duration_s": round(time.time() - start, 3),
        }

    def stats(self) -> dict:
        from cos.workflow.executor import workflow_executor
        return workflow_executor.stats()


workflow_orchestrator = WorkflowOrchestrator()
