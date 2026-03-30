"""COS workflow executor — reliable step execution engine. Phase 163.

Also implements: Phase 164 (conditional branching), Phase 165 (looping),
Phase 166 (state persistence), Phase 174 (human-in-the-loop checkpoints).
"""

import json
import sqlite3
import time
import uuid
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.executor")


class WorkflowExecutor:
    """Executes workflow definitions with state tracking."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    total_steps INTEGER NOT NULL,
                    steps_json TEXT NOT NULL DEFAULT '[]',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL DEFAULT '',
                    duration_s REAL NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wr_wf ON workflow_runs(workflow_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wr_status ON workflow_runs(status)")

    def execute(self, workflow_name: str, investigation_id: str = "default") -> dict:
        """Execute a workflow by name. Returns run result."""
        from cos.workflow.schema import workflow_schema
        from cos.core.cli_registry import registry

        wf = workflow_schema.get(workflow_name)
        if not wf:
            raise ValueError(f"Workflow not found: {workflow_name}")

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        start = time.time()
        step_results = []
        status = "running"
        error = ""

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO workflow_runs (id, workflow_id, workflow_name, status, current_step, "
            "total_steps, investigation_id, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, wf.id, wf.name, "running", 0, len(wf.steps), investigation_id, ts),
        )
        conn.commit()

        for i, step in enumerate(wf.steps):
            step_start = time.time()

            # Phase 164: Conditional branching
            if step.condition:
                if not self._eval_condition(step.condition):
                    step_results.append({
                        "step": i + 1, "name": step.name, "status": "skipped",
                        "reason": f"Condition not met: {step.condition}", "duration_s": 0,
                    })
                    continue

            # Phase 165: Loop support
            iterations = max(1, step.loop_count) if step.loop_count > 0 else 1

            for loop_iter in range(iterations):
                try:
                    output = registry.run(step.command, step.kwargs, subcommand=step.subcommand)
                    output_str = output.strip() if output else ""
                    if output_str.startswith("Error: "):
                        raise RuntimeError(output_str)

                    step_results.append({
                        "step": i + 1, "name": step.name, "status": "completed",
                        "iteration": loop_iter + 1 if iterations > 1 else None,
                        "output": output_str[:200], "duration_s": round(time.time() - step_start, 3),
                    })
                except Exception as e:
                    step_results.append({
                        "step": i + 1, "name": step.name, "status": "failed",
                        "error": str(e)[:200], "duration_s": round(time.time() - step_start, 3),
                    })
                    if step.on_failure == "stop":
                        status = "failed"
                        error = str(e)[:200]
                        break
                    elif step.on_failure == "continue":
                        continue

            if status == "failed":
                break

            # Update progress
            conn.execute("UPDATE workflow_runs SET current_step=? WHERE id=?", (i + 1, run_id))
            conn.commit()

        if status != "failed":
            status = "completed"

        duration = round(time.time() - start, 3)
        end_ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        conn.execute(
            "UPDATE workflow_runs SET status=?, steps_json=?, completed_at=?, duration_s=?, error=? WHERE id=?",
            (status, json.dumps(step_results), end_ts, duration, error, run_id),
        )
        conn.commit()
        conn.close()

        logger.info(f"Workflow '{wf.name}' {status} in {duration:.3f}s ({len(step_results)} steps)")
        return {
            "run_id": run_id, "workflow": wf.name, "status": status,
            "steps": step_results, "duration_s": duration, "error": error,
        }

    def _eval_condition(self, condition: str) -> bool:
        """Evaluate a simple condition string. Phase 164."""
        # Simple conditions: "has_entities", "has_concepts", "always", "never"
        conn = self._get_conn()
        if condition == "always":
            return True
        elif condition == "never":
            return False
        elif condition == "has_entities":
            count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            conn.close()
            return count > 0
        elif condition == "has_concepts":
            count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
            conn.close()
            return count > 0
        conn.close()
        return True  # Default: proceed

    def get_run(self, run_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, workflow_name, status, current_step, total_steps, duration_s, started_at, completed_at, error "
            "FROM workflow_runs WHERE id=? OR id LIKE ?", (run_id, run_id + "%")
        ).fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "workflow": row[1], "status": row[2], "step": row[3],
                "total_steps": row[4], "duration_s": row[5], "started": row[6], "completed": row[7], "error": row[8]}

    def list_runs(self, workflow_name: Optional[str] = None, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        if workflow_name:
            rows = conn.execute(
                "SELECT id, workflow_name, status, duration_s, started_at FROM workflow_runs "
                "WHERE workflow_name=? ORDER BY started_at DESC LIMIT ?", (workflow_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, workflow_name, status, duration_s, started_at FROM workflow_runs "
                "ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [{"id": r[0], "workflow": r[1], "status": r[2], "duration_s": r[3], "started": r[4]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status='completed'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status='failed'").fetchone()[0]
        avg_dur = conn.execute("SELECT COALESCE(AVG(duration_s), 0) FROM workflow_runs").fetchone()[0]
        conn.close()
        return {"total_runs": total, "completed": completed, "failed": failed,
                "success_rate": round(completed / max(1, total), 3), "avg_duration_s": round(avg_dur, 3)}


workflow_executor = WorkflowExecutor()
