"""COS token + cost tracking middleware.

Records every API call's token usage and cost in SQLite.
Tracks per-investigation totals and enforces budget warnings.

Usage:
    from cos.core.cost import cost_tracker
    cost_tracker.record("claude-haiku-4-5-20251001", input_tokens=500, output_tokens=100,
                        investigation_id="inv-001", operation="classify")
    print(cost_tracker.get_total("inv-001"))
"""

import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.core.cost")

# Pricing per million tokens (input, output) in USD
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6": (15.00, 75.00),
    # Defaults for unknown models
    "default": (1.00, 5.00),
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    cost = (input_tokens / 1_000_000 * pricing[0]) + (output_tokens / 1_000_000 * pricing[1])
    return round(cost, 6)


@dataclass
class CostEvent:
    timestamp: str
    investigation_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    operation: str


class CostTracker:
    """Persistent cost tracking via SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    operation TEXT NOT NULL DEFAULT ''
                )
            """)

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        investigation_id: str = "default",
        operation: str = "",
    ) -> float:
        """Record a cost event. Returns the computed cost."""
        cost = compute_cost(model, input_tokens, output_tokens)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO cost_events (timestamp, investigation_id, model, input_tokens, output_tokens, cost_usd, operation) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts, investigation_id, model, input_tokens, output_tokens, cost, operation),
            )

        # Log with structured fields
        logger.info(
            f"Cost: ${cost:.4f} ({model}, {input_tokens}+{output_tokens} tokens)",
            extra={"cost": cost, "investigation_id": investigation_id, "tokens": input_tokens + output_tokens},
        )

        # Budget warning check
        total = self.get_total(investigation_id)
        threshold = settings.cost_budget_per_investigation * settings.cost_warning_threshold
        if total > threshold:
            logger.warning(
                f"Budget warning: investigation '{investigation_id}' at ${total:.4f} "
                f"(threshold: ${threshold:.4f}, budget: ${settings.cost_budget_per_investigation:.2f})",
                extra={"investigation_id": investigation_id, "cost": total},
            )

        return cost

    def get_total(self, investigation_id: str = "default") -> float:
        """Get total cost for an investigation."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchone()
        return row[0]

    def get_summary(self) -> dict:
        """Get full cost summary: total, per-model, per-investigation."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events").fetchone()[0]
            total_events = conn.execute("SELECT COUNT(*) FROM cost_events").fetchone()[0]

            by_model = conn.execute(
                "SELECT model, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_usd) "
                "FROM cost_events GROUP BY model ORDER BY SUM(cost_usd) DESC"
            ).fetchall()

            by_investigation = conn.execute(
                "SELECT investigation_id, COUNT(*), SUM(cost_usd) "
                "FROM cost_events GROUP BY investigation_id ORDER BY SUM(cost_usd) DESC"
            ).fetchall()

        return {
            "total_cost": round(total, 6),
            "total_events": total_events,
            "by_model": [
                {"model": m, "events": n, "input_tokens": it, "output_tokens": ot, "cost": round(c, 6)}
                for m, n, it, ot, c in by_model
            ],
            "by_investigation": [
                {"investigation_id": inv, "events": n, "cost": round(c, 6)}
                for inv, n, c in by_investigation
            ],
        }

    def reset(self):
        """Clear all cost events (use with caution)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM cost_events")
        logger.info("Cost tracker reset — all events cleared")


# Singleton
cost_tracker = CostTracker()
