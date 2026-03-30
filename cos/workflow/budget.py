"""COS cost budget constraints — control workflow spending. Phase 171."""

import sqlite3
import time
import uuid
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.workflow.budget")


class BudgetManager:
    """Manages cost budgets for workflows and investigations."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    budget_usd REAL NOT NULL,
                    spent_usd REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    UNIQUE(target_type, target_id)
                )
            """)

    def set_budget(self, target_type: str, target_id: str, budget_usd: float) -> str:
        """Set a cost budget. Returns budget ID."""
        bid = f"bgt-{uuid.uuid4().hex[:8]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO budgets (id, target_type, target_id, budget_usd, spent_usd, status, created_at) "
                "VALUES (?, ?, ?, ?, 0, 'active', ?)",
                (bid, target_type, target_id, budget_usd, ts),
            )
        logger.info(f"Budget set: {target_type}/{target_id} = ${budget_usd:.2f}")
        return bid

    def check_budget(self, target_type: str, target_id: str) -> dict:
        """Check budget status."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT budget_usd, spent_usd, status FROM budgets WHERE target_type=? AND target_id=?",
            (target_type, target_id),
        ).fetchone()
        conn.close()
        if not row:
            return {"has_budget": False}
        remaining = row[0] - row[1]
        return {"has_budget": True, "budget": row[0], "spent": row[1],
                "remaining": round(remaining, 4), "status": row[2],
                "exceeded": remaining < 0}

    def record_spend(self, target_type: str, target_id: str, amount_usd: float) -> bool:
        """Record spending against a budget. Returns True if within budget."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE budgets SET spent_usd = spent_usd + ? WHERE target_type=? AND target_id=?",
                (amount_usd, target_type, target_id),
            )
            row = conn.execute(
                "SELECT budget_usd, spent_usd FROM budgets WHERE target_type=? AND target_id=?",
                (target_type, target_id),
            ).fetchone()
            if row and row[1] > row[0]:
                conn.execute(
                    "UPDATE budgets SET status='exceeded' WHERE target_type=? AND target_id=?",
                    (target_type, target_id),
                )
                return False
        return True

    def list_budgets(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT target_type, target_id, budget_usd, spent_usd, status, created_at FROM budgets ORDER BY created_at"
        ).fetchall()
        conn.close()
        return [{"type": r[0], "id": r[1], "budget": r[2], "spent": r[3], "status": r[4], "created_at": r[5]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]
        total_budget = conn.execute("SELECT COALESCE(SUM(budget_usd), 0) FROM budgets").fetchone()[0]
        total_spent = conn.execute("SELECT COALESCE(SUM(spent_usd), 0) FROM budgets").fetchone()[0]
        conn.close()
        return {"total_budgets": total, "total_budget_usd": round(total_budget, 4),
                "total_spent_usd": round(total_spent, 4)}


budget_manager = BudgetManager()
