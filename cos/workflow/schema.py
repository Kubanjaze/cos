"""COS workflow definition schema (DSL) — formalize workflows. Phase 161.

Defines the canonical workflow schema: steps, inputs, outputs, conditions.
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.schema")


@dataclass
class WorkflowStep:
    name: str
    command: str
    subcommand: Optional[str] = None
    kwargs: dict = field(default_factory=dict)
    condition: Optional[str] = None  # Phase 164
    loop_count: int = 0  # Phase 165
    on_failure: str = "stop"  # stop | continue | retry


@dataclass
class WorkflowDef:
    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    domain: str = "general"
    version: int = 1
    investigation_id: str = "default"
    created_at: str = ""


class WorkflowSchema:
    """Manages workflow definitions with versioned DSL."""

    _COLS = "id, name, description, steps_json, domain, version, investigation_id, created_at"

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_defs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_lower TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    steps_json TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT 'general',
                    version INTEGER NOT NULL DEFAULT 1,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_wfd_name ON workflow_defs(name_lower)")

    def define(self, name: str, steps: list[dict], description: str = "",
               domain: str = "general", investigation_id: str = "default") -> str:
        """Define a new workflow. Returns workflow def ID."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        wid = f"wfd-{uuid.uuid4().hex[:8]}"
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO workflow_defs (id, name, name_lower, description, steps_json, domain, version, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (wid, name.strip(), name.strip().lower(), description, json.dumps(steps), domain, 1, investigation_id, ts),
            )
        logger.info(f"Workflow defined: {name} ({len(steps)} steps)")
        return wid

    def get(self, name: str) -> Optional[WorkflowDef]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, name, description, steps_json, domain, version, investigation_id, created_at "
            "FROM workflow_defs WHERE name_lower=?", (name.strip().lower(),)
        ).fetchone()
        conn.close()
        if not row:
            return None
        steps = [WorkflowStep(**s) for s in json.loads(row[3])]
        return WorkflowDef(id=row[0], name=row[1], description=row[2], steps=steps,
                          domain=row[4], version=row[5], investigation_id=row[6], created_at=row[7])

    def list_workflows(self, domain: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if domain:
            rows = conn.execute(
                "SELECT id, name, description, domain, version, created_at FROM workflow_defs WHERE domain=? ORDER BY name",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, description, domain, version, created_at FROM workflow_defs ORDER BY name"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "description": r[2], "domain": r[3], "version": r[4], "created_at": r[5]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM workflow_defs").fetchone()[0]
        conn.close()
        return {"total_workflows": total}


workflow_schema = WorkflowSchema()
