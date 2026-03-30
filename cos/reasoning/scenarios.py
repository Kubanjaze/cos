"""COS scenario generator — explore what could happen next.

Phase 150: Generates possible future scenarios based on current evidence.
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.scenarios")


class ScenarioGenerator:
    """Generates possible scenarios from current knowledge state."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL DEFAULT '[]',
                    likelihood REAL NOT NULL DEFAULT 0.5,
                    impact TEXT NOT NULL DEFAULT 'medium',
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def generate(self, context: str = "general", investigation_id: str = "default") -> list[dict]:
        """Generate scenarios based on current knowledge."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        scenarios = []

        # Generate scenarios from scaffold patterns
        rows = conn.execute("""
            SELECT target_value, COUNT(*) FROM entity_relations
            WHERE relation_type='belongs_to_scaffold' GROUP BY target_value ORDER BY COUNT(*) DESC LIMIT 5
        """).fetchall()

        for scaffold, count in rows:
            # Best case scenario
            sid = f"scn-{uuid.uuid4().hex[:8]}"
            scenario = {
                "id": sid, "title": f"Best case: {scaffold} scaffold expansion",
                "description": f"If {scaffold} scaffold ({count} compounds) shows consistent SAR, expanding with new substituents could yield improved potency.",
                "assumptions": [f"{scaffold} SAR is transferable", "No toxicity cliffs"],
                "likelihood": 0.6, "impact": "high",
            }
            conn.execute(
                "INSERT INTO scenarios (id, title, description, assumptions_json, likelihood, impact, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, scenario["title"], scenario["description"],
                 json.dumps(scenario["assumptions"]), scenario["likelihood"], scenario["impact"],
                 investigation_id, ts),
            )
            scenarios.append(scenario)

        conn.commit()
        conn.close()
        logger.info(f"Generated {len(scenarios)} scenarios")
        return scenarios

    def list_scenarios(self, investigation_id: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if investigation_id:
            rows = conn.execute(
                "SELECT id, title, likelihood, impact, created_at FROM scenarios WHERE investigation_id=? ORDER BY likelihood DESC",
                (investigation_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, title, likelihood, impact, created_at FROM scenarios ORDER BY likelihood DESC").fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "likelihood": r[2], "impact": r[3], "created_at": r[4]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
        avg_like = conn.execute("SELECT COALESCE(AVG(likelihood), 0) FROM scenarios").fetchone()[0]
        conn.close()
        return {"total": total, "avg_likelihood": round(avg_like, 3)}


scenario_generator = ScenarioGenerator()
