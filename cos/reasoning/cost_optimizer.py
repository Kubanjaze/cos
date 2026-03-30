"""COS reasoning cost optimizer — minimize cost per reasoning pass. Phase 159."""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.cost_optimizer")


class ReasoningCostOptimizer:
    """Optimizes reasoning operations for cost efficiency."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def analyze_costs(self) -> dict:
        """Analyze reasoning costs across the system."""
        conn = self._get_conn()

        # Cost from cost_events table
        total_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events").fetchone()[0]
        event_count = conn.execute("SELECT COUNT(*) FROM cost_events").fetchone()[0]

        # Episode costs
        episode_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM episodes").fetchone()[0]

        # Reasoning artifact counts (proxy for compute)
        try:
            syntheses = conn.execute("SELECT COUNT(*) FROM syntheses").fetchone()[0]
        except Exception:
            syntheses = 0
        try:
            hypotheses = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
        except Exception:
            hypotheses = 0

        conn.close()

        # Recommendations
        recommendations = []
        if event_count > 100:
            recommendations.append("Consider caching frequent queries to reduce API calls")
        if syntheses > 0 and total_cost > 0:
            cost_per_synthesis = total_cost / max(1, syntheses)
            if cost_per_synthesis > 0.10:
                recommendations.append(f"Cost per synthesis (${cost_per_synthesis:.4f}) is high — use cheaper models for drafts")

        return {
            "total_api_cost": round(total_cost, 4),
            "total_episode_cost": round(episode_cost, 4),
            "api_calls": event_count,
            "syntheses": syntheses,
            "hypotheses": hypotheses,
            "cost_per_operation": round(total_cost / max(1, event_count), 6),
            "recommendations": recommendations if recommendations else ["Cost is within normal range"],
        }

    def suggest_optimizations(self) -> list[dict]:
        """Suggest cost optimizations."""
        conn = self._get_conn()
        suggestions = []

        # Check cache hit rate
        try:
            active = conn.execute("SELECT COUNT(*) FROM cache WHERE expires_at > datetime('now')").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if total > 0 and active / total < 0.5:
                suggestions.append({"type": "cache", "suggestion": "Increase cache TTL — high expiration rate",
                                   "impact": "medium"})
        except Exception:
            pass

        # Check for redundant scoring
        scored = conn.execute("SELECT COUNT(*) FROM memory_scores").fetchone()[0]
        if scored > 200:
            suggestions.append({"type": "scoring", "suggestion": "Score only active investigation items, not all",
                               "impact": "low"})

        conn.close()

        if not suggestions:
            suggestions.append({"type": "general", "suggestion": "System is cost-efficient at current scale",
                               "impact": "none"})

        return suggestions

    def stats(self) -> dict:
        return self.analyze_costs()


reasoning_cost_optimizer = ReasoningCostOptimizer()
