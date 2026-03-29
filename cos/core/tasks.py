"""COS async task queue — background job execution.

SQLite-backed task queue with sequential worker. No external broker needed.

Usage:
    from cos.core.tasks import task_queue
    task_id = task_queue.submit("cos ingest data/compounds.csv", investigation_id="inv-001")
    task_queue.run_next()  # process one pending task
    print(task_queue.get_status(task_id))
"""

import os
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.tasks")


@dataclass
class Task:
    id: str
    status: str  # pending, running, completed, failed
    command: str
    investigation_id: str
    submitted_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result_path: Optional[str]
    error: Optional[str]


class TaskQueue:
    """SQLite-backed task queue with sequential worker."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._tasks_dir = Path(settings.storage_dir) / "tasks"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    command TEXT NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    submitted_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_path TEXT,
                    error TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_investigation ON tasks(investigation_id)")

    def submit(self, command: str, investigation_id: str = "default") -> str:
        """Submit a task to the queue. Returns task ID."""
        task_id = str(uuid.uuid4())
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (id, status, command, investigation_id, submitted_at) VALUES (?, 'pending', ?, ?, ?)",
                (task_id, command, investigation_id, ts),
            )
        logger.info(f"Task submitted: {task_id[:8]}... '{command[:50]}'",
                     extra={"investigation_id": investigation_id})
        return task_id

    def run_next(self) -> Optional[str]:
        """Pick and execute the oldest pending task. Returns task_id or None."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, command, investigation_id FROM tasks WHERE status='pending' ORDER BY submitted_at LIMIT 1"
        ).fetchone()

        if not row:
            logger.info("No pending tasks")
            conn.close()
            return None

        task_id, command, inv_id = row
        started = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute("UPDATE tasks SET status='running', started_at=? WHERE id=?", (started, task_id))
        conn.commit()
        conn.close()

        logger.info(f"Running task {task_id[:8]}...: {command[:50]}",
                     extra={"investigation_id": inv_id})

        # Execute as subprocess
        result_path = str(self._tasks_dir / f"{task_id}.txt")
        try:
            python = sys.executable
            # Parse command: if it starts with "cos", run as "python -m cos ..."
            if command.startswith("cos "):
                cmd_parts = [python, "-m"] + command.split()
            else:
                cmd_parts = command.split()

            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.getcwd(),
            )

            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nEXIT CODE: {result.returncode}"
            Path(result_path).write_text(output, encoding="utf-8")

            completed = time.strftime("%Y-%m-%dT%H:%M:%S")
            status = "completed" if result.returncode == 0 else "failed"
            error = result.stderr[:500] if result.returncode != 0 else None

            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET status=?, completed_at=?, result_path=?, error=? WHERE id=?",
                (status, completed, result_path, error, task_id),
            )
            conn.commit()
            conn.close()

            logger.info(f"Task {task_id[:8]}... {status}",
                         extra={"investigation_id": inv_id})

        except subprocess.TimeoutExpired:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET status='failed', completed_at=?, error='Timeout (300s)' WHERE id=?",
                (time.strftime("%Y-%m-%dT%H:%M:%S"), task_id),
            )
            conn.commit()
            conn.close()
            logger.warning(f"Task {task_id[:8]}... timed out")

        except Exception as e:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET status='failed', completed_at=?, error=? WHERE id=?",
                (time.strftime("%Y-%m-%dT%H:%M:%S"), str(e)[:500], task_id),
            )
            conn.commit()
            conn.close()
            logger.error(f"Task {task_id[:8]}... error: {e}")

        return task_id

    def run_worker(self, max_tasks: int = 10):
        """Process up to max_tasks pending tasks sequentially."""
        processed = 0
        while processed < max_tasks:
            task_id = self.run_next()
            if task_id is None:
                break
            processed += 1
        logger.info(f"Worker finished: processed {processed} tasks")
        return processed

    def get_status(self, task_id: str) -> Optional[Task]:
        """Get task details by full or partial ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, status, command, investigation_id, submitted_at, started_at, completed_at, result_path, error "
            "FROM tasks WHERE id=? OR id LIKE ?",
            (task_id, task_id + "%"),
        ).fetchone()
        conn.close()
        if not row:
            return None
        return Task(*row)

    def list_tasks(self, status: Optional[str] = None, limit: int = 20) -> list[Task]:
        """List tasks, optionally filtered by status."""
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT id, status, command, investigation_id, submitted_at, started_at, completed_at, result_path, error "
                "FROM tasks WHERE status=? ORDER BY submitted_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, status, command, investigation_id, submitted_at, started_at, completed_at, result_path, error "
                "FROM tasks ORDER BY submitted_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [Task(*r) for r in rows]


# Singleton
task_queue = TaskQueue()
