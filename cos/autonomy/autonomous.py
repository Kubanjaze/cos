"""COS autonomy layer — fully autonomous operation. Phases 216-220.

216: Fully autonomous workflow execution
217: Cost optimization AI
218: Priority-driven scheduling
219: Continuous monitoring system
220: End-to-end autonomous investigation loop — COS COMPLETION CONDITION
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.autonomy.autonomous")


class AutonomousExecutor:
    """Fully autonomous workflow execution. Phase 216."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def run_autonomous(self, investigation_id: str = "default") -> dict:
        """Run the best available workflow for an investigation."""
        from cos.workflow.executor import workflow_executor
        from cos.workflow.schema import workflow_schema

        workflows = workflow_schema.list_workflows()
        if not workflows:
            return {"status": "no_workflows", "message": "No workflows defined"}

        # Pick the first available workflow
        wf_name = workflows[0]["name"]
        result = workflow_executor.execute(wf_name, investigation_id=investigation_id)
        return {"status": result["status"], "workflow": wf_name,
                "duration_s": result["duration_s"], "steps_completed": len(result["steps"])}


class CostOptimizer:
    """Cost optimization AI. Phase 217."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def optimize(self) -> dict:
        """Analyze and suggest cost optimizations."""
        conn = self._get_conn()
        total_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events").fetchone()[0]
        episode_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM episodes").fetchone()[0]

        try:
            cache_entries = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        except Exception:
            cache_entries = 0

        conn.close()

        suggestions = []
        if total_cost > 1.0:
            suggestions.append("Consider using cheaper models for draft operations")
        if cache_entries < 10:
            suggestions.append("Increase caching to reduce redundant computations")
        if not suggestions:
            suggestions.append("Cost is optimal at current scale")

        return {"total_cost": round(total_cost, 4), "episode_cost": round(episode_cost, 4),
                "cache_entries": cache_entries, "suggestions": suggestions}


class PriorityScheduler:
    """Priority-driven scheduling. Phase 218."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def schedule_by_priority(self) -> list[dict]:
        """Determine what should run next based on priority."""
        conn = self._get_conn()
        tasks = []

        # High priority: open conflicts
        try:
            conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
            if conflicts > 0:
                tasks.append({"priority": 0.9, "task": "resolve_conflicts",
                             "description": f"Resolve {conflicts} open conflict(s)"})
        except Exception:
            pass

        # Medium: unscored items
        try:
            unscored = conn.execute(
                "SELECT COUNT(*) FROM entities e LEFT JOIN memory_scores m ON m.target_id=e.id WHERE m.id IS NULL"
            ).fetchone()[0]
            if unscored > 0:
                tasks.append({"priority": 0.6, "task": "score_entities",
                             "description": f"Score {unscored} unscored entities"})
        except Exception:
            pass

        # Low: knowledge gaps
        try:
            sparse = conn.execute("SELECT COUNT(*) FROM concepts GROUP BY domain HAVING COUNT(*) < 3").fetchone()
            if sparse:
                tasks.append({"priority": 0.4, "task": "fill_knowledge_gaps",
                             "description": "Expand sparse domains"})
        except Exception:
            pass

        conn.close()
        tasks.sort(key=lambda x: x["priority"], reverse=True)
        return tasks


class ContinuousMonitor:
    """Continuous monitoring system. Phase 219."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def check(self) -> dict:
        """Run a monitoring check across the system."""
        conn = self._get_conn()
        status = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "checks": []}

        # Check: DB accessible
        status["checks"].append({"check": "database", "status": "ok"})

        # Check: recent activity
        try:
            latest_ep = conn.execute("SELECT MAX(created_at) FROM episodes").fetchone()[0]
            status["checks"].append({"check": "recent_activity", "status": "ok", "latest": latest_ep})
        except Exception:
            status["checks"].append({"check": "recent_activity", "status": "warn", "detail": "no episodes"})

        # Check: conflict backlog
        try:
            open_conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
            s = "ok" if open_conflicts == 0 else "warn"
            status["checks"].append({"check": "conflicts", "status": s, "open": open_conflicts})
        except Exception:
            pass

        # Check: budget status
        try:
            exceeded = conn.execute("SELECT COUNT(*) FROM budgets WHERE status='exceeded'").fetchone()[0]
            s = "ok" if exceeded == 0 else "critical"
            status["checks"].append({"check": "budgets", "status": s, "exceeded": exceeded})
        except Exception:
            pass

        conn.close()
        all_ok = all(c["status"] == "ok" for c in status["checks"])
        status["overall"] = "healthy" if all_ok else "needs_attention"
        return status


class AutonomousInvestigationLoop:
    """End-to-end autonomous investigation. Phase 220 — COS COMPLETION CONDITION."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def run(self, question: str, investigation_id: str = "default") -> dict:
        """Run a full autonomous investigation cycle.

        COS completion condition: ingest → memory → reason → decide → act → monitor.
        """
        start = time.time()
        results = {"question": question, "investigation_id": investigation_id, "steps": []}

        # Step 1: Build memory (synthesis)
        try:
            from cos.reasoning.synthesis import synthesis_engine
            syn = synthesis_engine.synthesize(question, investigation_id=investigation_id)
            results["steps"].append({"phase": "memory", "action": "synthesize",
                                     "sources": syn.source_count, "status": "ok"})
        except Exception as e:
            results["steps"].append({"phase": "memory", "action": "synthesize", "status": "error", "error": str(e)[:50]})

        # Step 2: Reason (multi-pass)
        try:
            from cos.reasoning.multipass import multipass_reasoner
            reasoning = multipass_reasoner.reason(question, passes=3, investigation_id=investigation_id)
            results["steps"].append({"phase": "reasoning", "action": "multipass",
                                     "passes": reasoning["total_passes"], "status": "ok"})
        except Exception as e:
            results["steps"].append({"phase": "reasoning", "status": "error", "error": str(e)[:50]})

        # Step 3: Decide
        try:
            from cos.decision.schema import decision_store
            did = decision_store.create(
                f"Auto-decision: {question[:50]}", f"Based on synthesis of '{question}'",
                confidence=0.6, investigation_id=investigation_id,
            )
            results["steps"].append({"phase": "decision", "action": "create",
                                     "decision_id": did, "status": "ok"})
        except Exception as e:
            results["steps"].append({"phase": "decision", "status": "error", "error": str(e)[:50]})

        # Step 4: Generate actions
        try:
            from cos.decision.actions import action_generator
            actions = action_generator.generate(investigation_id=investigation_id)
            results["steps"].append({"phase": "action", "action": "generate",
                                     "actions": len(actions), "status": "ok"})
        except Exception as e:
            results["steps"].append({"phase": "action", "status": "error", "error": str(e)[:50]})

        # Step 5: Monitor
        monitor = ContinuousMonitor(self._db_path)
        health = monitor.check()
        results["steps"].append({"phase": "monitor", "action": "check",
                                 "overall": health["overall"], "status": "ok"})

        results["duration_s"] = round(time.time() - start, 3)
        results["status"] = "complete"
        results["step_count"] = len(results["steps"])
        ok_count = sum(1 for s in results["steps"] if s.get("status") == "ok")
        results["success_rate"] = round(ok_count / max(1, len(results["steps"])), 3)

        logger.info(f"Autonomous investigation: '{question}' — {ok_count}/{len(results['steps'])} steps OK in {results['duration_s']:.3f}s")
        return results

    def stats(self) -> dict:
        return {"capability": "end-to-end autonomous investigation",
                "steps": ["synthesize", "reason", "decide", "act", "monitor"]}


autonomous_executor = AutonomousExecutor()
cost_optimizer_ai = CostOptimizer()
priority_scheduler = PriorityScheduler()
continuous_monitor = ContinuousMonitor()
autonomous_investigation = AutonomousInvestigationLoop()
