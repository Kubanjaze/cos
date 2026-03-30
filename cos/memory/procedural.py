"""COS procedural memory — persistent reusable procedures.

Procedural memory answers "how do we do things?" — saved step-by-step workflows
that can be recalled, adapted, and re-executed with execution feedback tracking.

Distinct from pipelines (Phase 114, in-memory/code-defined) and episodic memory
(Phase 126, "what happened?") and semantic memory (Phase 127, "what we know?").

Usage:
    from cos.memory.procedural import procedural_memory
    procedural_memory.define("my-workflow", [
        {"command": "status"},
        {"command": "config", "subcommand": "validate"},
    ], description="Check system health")
    result = procedural_memory.run("my-workflow", investigation_id="inv-001")
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.procedural")


@dataclass
class Procedure:
    id: str
    name: str
    description: str
    domain: str
    category: str
    steps_json: str
    steps_schema_version: int
    source_ref: str
    success_count: int
    fail_count: int
    last_run_at: str
    last_run_status: str
    investigation_id: str
    created_at: str
    updated_at: str

    @property
    def steps(self) -> list[dict]:
        return json.loads(self.steps_json)

    @property
    def total_runs(self) -> int:
        return self.success_count + self.fail_count

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.success_count / self.total_runs


def _validate_steps(steps: list[dict]) -> None:
    """Validate steps against command registry. Raises ValueError on invalid."""
    from cos.core.cli_registry import registry

    if not isinstance(steps, list) or len(steps) == 0:
        raise ValueError("Steps must be a non-empty list")

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i+1}: must be a dict, got {type(step).__name__}")
        if "command" not in step:
            raise ValueError(f"Step {i+1}: missing required 'command' key")
        cmd = step["command"]
        if not isinstance(cmd, str):
            raise ValueError(f"Step {i+1}: 'command' must be a string")
        if cmd not in registry._commands:
            raise ValueError(f"Step {i+1}: unknown command '{cmd}'")
        if "kwargs" in step and not isinstance(step["kwargs"], dict):
            raise ValueError(f"Step {i+1}: 'kwargs' must be a dict")
        if "subcommand" in step:
            sub = step["subcommand"]
            if not isinstance(sub, str):
                raise ValueError(f"Step {i+1}: 'subcommand' must be a string")
            reg_cmd = registry._commands[cmd]
            if sub not in reg_cmd.subcommands:
                raise ValueError(f"Step {i+1}: unknown subcommand '{cmd} {sub}'")


class ProceduralMemory:
    """Persistent procedure store — procedural memory layer."""

    _COLS = (
        "id, name, description, domain, category, steps_json, steps_schema_version, "
        "source_ref, success_count, fail_count, last_run_at, last_run_status, "
        "investigation_id, created_at, updated_at"
    )

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS procedures (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_lower TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL DEFAULT 'general',
                    category TEXT NOT NULL DEFAULT 'general',
                    steps_json TEXT NOT NULL,
                    steps_schema_version INTEGER NOT NULL DEFAULT 1,
                    source_ref TEXT NOT NULL DEFAULT '',
                    success_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    last_run_at TEXT NOT NULL DEFAULT '',
                    last_run_status TEXT NOT NULL DEFAULT '',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_proc_name ON procedures(name_lower)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_proc_domain ON procedures(domain)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_proc_category ON procedures(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_proc_inv ON procedures(investigation_id)"
            )

    def define(
        self,
        name: str,
        steps: list[dict],
        description: str = "",
        domain: str = "general",
        category: str = "general",
        source_ref: str = "",
        investigation_id: str = "default",
    ) -> str:
        """Define a new procedure. Validates commands at define-time. Returns procedure ID."""
        _validate_steps(steps)

        name_lower = name.strip().lower()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM procedures WHERE name_lower=?", (name_lower,)
            ).fetchone()
            if existing:
                raise ValueError(
                    f"Procedure '{name}' already exists (id={existing[0]}). "
                    "Use update() to modify it."
                )

            proc_id = f"pro-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO procedures (id, name, name_lower, description, domain, category, "
                "steps_json, steps_schema_version, source_ref, success_count, fail_count, "
                "last_run_at, last_run_status, investigation_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (proc_id, name.strip(), name_lower, description, domain, category,
                 json.dumps(steps), 1, source_ref, 0, 0, "", "", investigation_id, ts, ts),
            )

        logger.info(f"Procedure defined: {name} ({len(steps)} steps, domain={domain})",
                     extra={"investigation_id": investigation_id})
        return proc_id

    def get(self, name: str) -> Optional[Procedure]:
        """Get a procedure by name (case-insensitive)."""
        conn = self._get_conn()
        row = conn.execute(
            f"SELECT {self._COLS} FROM procedures WHERE name_lower=?",
            (name.strip().lower(),),
        ).fetchone()
        conn.close()
        if not row:
            return None
        return Procedure(*row)

    def list_procedures(
        self,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[Procedure]:
        """List procedures with optional filters, ordered by success_count DESC."""
        conn = self._get_conn()
        conditions: list[str] = []
        params: list = []

        if domain:
            conditions.append("domain=?")
            params.append(domain)
        if category:
            conditions.append("category=?")
            params.append(category)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"SELECT {self._COLS} FROM procedures WHERE {where} "
            f"ORDER BY success_count DESC, name_lower LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [Procedure(*r) for r in rows]

    def run(self, name: str, investigation_id: str = "default") -> dict:
        """Execute a procedure's steps. Returns result dict."""
        from cos.core.cli_registry import registry

        proc = self.get(name)
        if not proc:
            raise ValueError(f"Procedure not found: {name}")

        steps = proc.steps
        logger.info(
            f"Running procedure '{proc.name}' ({len(steps)} steps)",
            extra={"investigation_id": investigation_id},
        )

        result = {
            "procedure": proc.name,
            "procedure_id": proc.id,
            "investigation_id": investigation_id,
            "steps": [],
            "status": "running",
        }
        start = time.time()
        succeeded = False

        try:
            for i, step in enumerate(steps):
                step_start = time.time()
                cmd = step["command"]
                kwargs = step.get("kwargs", {})
                subcmd = step.get("subcommand")

                try:
                    output = registry.run(cmd, kwargs, subcommand=subcmd)
                    output_stripped = output.strip() if output else ""
                    # Registry swallows exceptions and returns "Error: ..." strings
                    if output_stripped.startswith("Error: "):
                        raise RuntimeError(output_stripped)
                    step_result = {
                        "step": i + 1,
                        "command": cmd,
                        "subcommand": subcmd,
                        "status": "completed",
                        "output": output_stripped,
                        "duration_s": round(time.time() - step_start, 3),
                    }
                except Exception as e:
                    step_result = {
                        "step": i + 1,
                        "command": cmd,
                        "subcommand": subcmd,
                        "status": "failed",
                        "error": str(e),
                        "duration_s": round(time.time() - step_start, 3),
                    }
                    result["steps"].append(step_result)
                    result["status"] = "failed"
                    result["total_duration_s"] = round(time.time() - start, 3)
                    logger.error(f"Procedure '{proc.name}' failed at step {i+1}: {e}")
                    return result

                result["steps"].append(step_result)

            result["status"] = "completed"
            result["total_duration_s"] = round(time.time() - start, 3)
            succeeded = True

            logger.info(
                f"Procedure '{proc.name}' completed in {result['total_duration_s']:.3f}s",
                extra={"investigation_id": investigation_id},
            )
            return result

        finally:
            ts = time.strftime("%Y-%m-%dT%H:%M:%S")
            status = "completed" if succeeded else "failed"
            with self._get_conn() as conn:
                if succeeded:
                    conn.execute(
                        "UPDATE procedures SET success_count=success_count+1, "
                        "last_run_at=?, last_run_status=?, updated_at=? WHERE id=?",
                        (ts, status, ts, proc.id),
                    )
                else:
                    conn.execute(
                        "UPDATE procedures SET fail_count=fail_count+1, "
                        "last_run_at=?, last_run_status=?, updated_at=? WHERE id=?",
                        (ts, status, ts, proc.id),
                    )

    def update(
        self,
        name: str,
        description: Optional[str] = None,
        steps: Optional[list[dict]] = None,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> bool:
        """Update specific fields of an existing procedure. Returns True if found."""
        if steps is not None:
            _validate_steps(steps)

        name_lower = name.strip().lower()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM procedures WHERE name_lower=?", (name_lower,)
            ).fetchone()
            if not existing:
                return False

            updates = ["updated_at=?"]
            params: list = [ts]

            if description is not None:
                updates.append("description=?")
                params.append(description)
            if steps is not None:
                updates.append("steps_json=?")
                params.append(json.dumps(steps))
            if domain is not None:
                updates.append("domain=?")
                params.append(domain)
            if category is not None:
                updates.append("category=?")
                params.append(category)
            if source_ref is not None:
                updates.append("source_ref=?")
                params.append(source_ref)

            params.append(existing[0])
            conn.execute(
                f"UPDATE procedures SET {', '.join(updates)} WHERE id=?",
                params,
            )

        logger.info(f"Procedure updated: {name}")
        return True

    def delete(self, name: str) -> bool:
        """Delete a procedure by name (case-insensitive). Returns True if found."""
        name_lower = name.strip().lower()
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM procedures WHERE name_lower=?", (name_lower,)
            ).fetchone()
            if not existing:
                return False
            conn.execute("DELETE FROM procedures WHERE id=?", (existing[0],))

        logger.info(f"Procedure deleted: {name}")
        return True

    def stats(self) -> dict:
        """Return procedure statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM procedures").fetchone()[0]
        total_success = conn.execute(
            "SELECT COALESCE(SUM(success_count), 0) FROM procedures"
        ).fetchone()[0]
        total_fail = conn.execute(
            "SELECT COALESCE(SUM(fail_count), 0) FROM procedures"
        ).fetchone()[0]
        by_domain = conn.execute(
            "SELECT domain, COUNT(*) FROM procedures GROUP BY domain ORDER BY COUNT(*) DESC"
        ).fetchall()
        by_category = conn.execute(
            "SELECT category, COUNT(*) FROM procedures GROUP BY category ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()

        total_runs = total_success + total_fail
        success_rate = round(total_success / total_runs, 3) if total_runs > 0 else 0.0

        return {
            "total": total,
            "total_runs": total_runs,
            "total_success": total_success,
            "total_fail": total_fail,
            "success_rate": success_rate,
            "by_domain": {d: c for d, c in by_domain},
            "by_category": {cat: c for cat, c in by_category},
        }


# Singleton
procedural_memory = ProceduralMemory()
