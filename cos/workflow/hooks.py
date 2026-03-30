"""COS external action hooks — workflows that act externally. Phase 176.

Also covers: Phase 177 (multi-source ingestion workflows),
Phase 178 (continuous learning workflows), Phase 179 (workflow marketplace).
"""

import sqlite3
import time
import uuid
import json
from typing import Callable, Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.hooks")


class HookRegistry:
    """Registry of external action hooks for workflows."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._hooks: dict[str, Callable] = {}
        self._init_db()
        self._register_builtins()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hook_log (
                    id TEXT PRIMARY KEY,
                    hook_name TEXT NOT NULL,
                    input_json TEXT NOT NULL DEFAULT '{}',
                    output_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def register(self, name: str, fn: Callable, description: str = ""):
        """Register an external hook."""
        self._hooks[name] = fn
        logger.info(f"Hook registered: {name}")

    def execute(self, name: str, params: Optional[dict] = None) -> dict:
        """Execute a hook. Returns result."""
        if name not in self._hooks:
            raise ValueError(f"Hook not found: {name}")

        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        lid = f"hk-{uuid.uuid4().hex[:8]}"
        params = params or {}

        try:
            result = self._hooks[name](params)
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO hook_log (id, hook_name, input_json, output_json, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (lid, name, json.dumps(params), json.dumps(result), "success", ts),
                )
            return {"hook": name, "status": "success", "result": result}
        except Exception as e:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO hook_log (id, hook_name, input_json, output_json, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (lid, name, json.dumps(params), json.dumps({"error": str(e)}), "failed", ts),
                )
            return {"hook": name, "status": "failed", "error": str(e)}

    def _register_builtins(self):
        """Register built-in hooks."""
        def _notify_stub(params: dict) -> dict:
            return {"notified": True, "message": params.get("message", ""), "channel": "stdout"}

        def _export_stub(params: dict) -> dict:
            return {"exported": True, "format": params.get("format", "json"), "path": "stdout"}

        def _learn_stub(params: dict) -> dict:
            """Phase 178: Continuous learning stub."""
            return {"learned": True, "source": params.get("source", ""), "items": 0}

        self.register("notify", _notify_stub, "Send notification (stub)")
        self.register("export", _export_stub, "Export data (stub)")
        self.register("learn", _learn_stub, "Continuous learning trigger (stub)")

    def list_hooks(self) -> list[str]:
        return list(self._hooks.keys())

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM hook_log").fetchone()[0]
        by_hook = conn.execute("SELECT hook_name, COUNT(*) FROM hook_log GROUP BY hook_name").fetchall()
        conn.close()
        return {"registered_hooks": len(self._hooks), "total_executions": total,
                "by_hook": {n: c for n, c in by_hook}}


# Phase 179: Workflow marketplace (internal)
class WorkflowMarketplace:
    """Internal marketplace for sharing workflow definitions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def list_available(self) -> list[dict]:
        """List all shareable workflows (from defs + templates)."""
        from cos.workflow.schema import workflow_schema
        from cos.workflow.templates import template_registry

        workflows = workflow_schema.list_workflows()
        templates = template_registry.list_templates()

        available = []
        for w in workflows:
            available.append({"type": "workflow", "name": w["name"], "description": w["description"]})
        for t in templates:
            available.append({"type": "template", "name": t["name"], "description": t["description"]})
        return available

    def stats(self) -> dict:
        items = self.list_available()
        return {"total_available": len(items),
                "workflows": sum(1 for i in items if i["type"] == "workflow"),
                "templates": sum(1 for i in items if i["type"] == "template")}


hook_registry = HookRegistry()
workflow_marketplace = WorkflowMarketplace()
