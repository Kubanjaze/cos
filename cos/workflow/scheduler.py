"""COS workflow scheduler — scheduled + event-triggered execution. Phase 167-168."""

import sqlite3
import time
import uuid
import json
from typing import Optional, Callable

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.scheduler")


class WorkflowScheduler:
    """Manages scheduled and event-triggered workflow execution."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._event_triggers: dict[str, list[dict]] = {}
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_schedules (
                    id TEXT PRIMARY KEY,
                    workflow_name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    cron_expr TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT NOT NULL DEFAULT '',
                    run_count INTEGER NOT NULL DEFAULT 0,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def schedule(self, workflow_name: str, cron_expr: str,
                 investigation_id: str = "default") -> str:
        """Schedule a workflow with cron expression."""
        sid = f"sch-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO workflow_schedules (id, workflow_name, schedule_type, cron_expr, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sid, workflow_name, "cron", cron_expr, investigation_id, ts),
            )
        logger.info(f"Scheduled: {workflow_name} ({cron_expr})")
        return sid

    def on_event(self, event_type: str, workflow_name: str,
                 investigation_id: str = "default") -> str:
        """Trigger workflow on event. Phase 168."""
        sid = f"sch-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO workflow_schedules (id, workflow_name, schedule_type, event_type, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sid, workflow_name, "event", event_type, investigation_id, ts),
            )

        self._event_triggers.setdefault(event_type, []).append({
            "workflow_name": workflow_name, "investigation_id": investigation_id,
        })
        logger.info(f"Event trigger: {event_type} → {workflow_name}")
        return sid

    def fire_event(self, event_type: str) -> int:
        """Fire an event, triggering registered workflows. Returns count triggered."""
        triggers = self._event_triggers.get(event_type, [])
        count = 0
        for t in triggers:
            try:
                from cos.workflow.executor import workflow_executor
                workflow_executor.execute(t["workflow_name"], investigation_id=t["investigation_id"])
                count += 1
            except Exception as e:
                logger.error(f"Event trigger failed: {e}")
        return count

    def list_schedules(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, workflow_name, schedule_type, cron_expr, event_type, enabled, run_count, created_at "
            "FROM workflow_schedules ORDER BY created_at"
        ).fetchall()
        conn.close()
        return [{"id": r[0], "workflow": r[1], "type": r[2], "cron": r[3], "event": r[4],
                 "enabled": bool(r[5]), "runs": r[6], "created_at": r[7]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM workflow_schedules").fetchone()[0]
        cron = conn.execute("SELECT COUNT(*) FROM workflow_schedules WHERE schedule_type='cron'").fetchone()[0]
        event = conn.execute("SELECT COUNT(*) FROM workflow_schedules WHERE schedule_type='event'").fetchone()[0]
        conn.close()
        return {"total_schedules": total, "cron": cron, "event_triggers": event,
                "in_memory_triggers": sum(len(v) for v in self._event_triggers.values())}


workflow_scheduler = WorkflowScheduler()
