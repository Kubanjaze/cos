"""COS workflow analytics — which workflows work best. Phase 172.

Also covers: Phase 173 (debugging/replay), Phase 175 (output standardization),
Phase 180 (workflow benchmarking).
"""

import json
import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.analytics")


class WorkflowAnalytics:
    """Analyzes workflow execution patterns and performance."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def performance_report(self) -> dict:
        """Generate workflow performance report."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT workflow_name, COUNT(*) as runs,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as ok,
                   AVG(duration_s) as avg_dur, MAX(duration_s) as max_dur
            FROM workflow_runs GROUP BY workflow_name ORDER BY runs DESC
        """).fetchall()
        conn.close()

        return {
            "workflows": [
                {"name": r[0], "runs": r[1], "completed": r[2],
                 "success_rate": round(r[2] / max(1, r[1]), 3),
                 "avg_duration_s": round(r[3], 3), "max_duration_s": round(r[4], 3)}
                for r in rows
            ],
        }

    def replay_run(self, run_id: str) -> dict:
        """Replay/inspect a workflow run. Phase 173."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, workflow_name, status, steps_json, duration_s, started_at, completed_at, error "
            "FROM workflow_runs WHERE id=? OR id LIKE ?", (run_id, run_id + "%")
        ).fetchone()
        conn.close()
        if not row:
            return {"error": "Run not found"}

        steps = json.loads(row[3]) if row[3] else []
        return {
            "run_id": row[0], "workflow": row[1], "status": row[2],
            "steps": steps, "duration_s": row[4],
            "started": row[5], "completed": row[6], "error": row[7],
        }

    def standardize_output(self, run_result: dict) -> dict:
        """Standardize workflow output format. Phase 175."""
        return {
            "run_id": run_result.get("run_id", ""),
            "workflow": run_result.get("workflow", ""),
            "status": run_result.get("status", "unknown"),
            "step_count": len(run_result.get("steps", [])),
            "completed_steps": sum(1 for s in run_result.get("steps", []) if s.get("status") == "completed"),
            "failed_steps": sum(1 for s in run_result.get("steps", []) if s.get("status") == "failed"),
            "duration_s": run_result.get("duration_s", 0),
            "error": run_result.get("error", ""),
        }

    def benchmark_workflows(self) -> dict:
        """Benchmark all workflows. Phase 180."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT workflow_name, COUNT(*) as runs, AVG(duration_s) as avg_dur,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
            FROM workflow_runs GROUP BY workflow_name HAVING runs >= 1 ORDER BY success_rate DESC, avg_dur
        """).fetchall()
        conn.close()

        benchmarks = []
        for name, runs, avg_dur, sr in rows:
            # Composite: success_rate * 0.6 + speed * 0.4
            speed_score = max(0, 1.0 - avg_dur / 10.0)
            composite = round(sr * 0.6 + speed_score * 0.4, 4)
            benchmarks.append({
                "workflow": name, "runs": runs, "success_rate": round(sr, 3),
                "avg_duration_s": round(avg_dur, 3), "composite": composite,
            })

        return {"benchmarks": benchmarks}

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        workflows = conn.execute("SELECT COUNT(DISTINCT workflow_name) FROM workflow_runs").fetchone()[0]
        conn.close()
        return {"total_runs": total, "unique_workflows": workflows}


workflow_analytics = WorkflowAnalytics()
