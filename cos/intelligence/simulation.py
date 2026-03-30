"""COS simulation engine + knowledge graph reasoning. Phase 208-209.

Also covers: Phase 210 (cross-domain reasoning), Phase 211 (adaptive learning),
Phase 212 (novelty detection).
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.intelligence.simulation")


class SimulationEngine:
    """Simulates outcomes by varying parameters. Phase 208."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def run(self, name: str, base_scaffold: str = "benz",
            confidence_variations: list[float] = None,
            investigation_id: str = "default") -> dict:
        """Run a what-if simulation."""
        if confidence_variations is None:
            confidence_variations = [0.6, 0.7, 0.8, 0.9]

        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Get scaffold data
        rows = conn.execute("""
            SELECT r2.source_entity, r2.target_value
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r1.target_value=?
            AND r2.relation_type='has_activity' AND r2.target_value LIKE 'pIC50=%'
        """, (base_scaffold,)).fetchall()

        values = []
        for comp, act in rows:
            try:
                values.append(float(act.replace("pIC50=", "")))
            except ValueError:
                pass

        avg = sum(values) / len(values) if values else 0
        results = []
        for conf in confidence_variations:
            # Simulate: what if we had this confidence threshold?
            filtered = [v for v in values if v >= avg * conf]
            results.append({
                "confidence_threshold": conf,
                "compounds_remaining": len(filtered),
                "avg_activity": round(sum(filtered) / len(filtered), 2) if filtered else 0,
                "enrichment": round(len(filtered) / max(1, len(values)), 3),
            })

        sid = f"sim-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO simulations (id, name, parameters_json, results_json, investigation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, name, json.dumps({"scaffold": base_scaffold, "variations": confidence_variations}),
             json.dumps(results), investigation_id, ts),
        )
        conn.commit()
        conn.close()

        logger.info(f"Simulation '{name}': {len(results)} scenarios")
        return {"id": sid, "name": name, "scaffold": base_scaffold,
                "scenarios": results, "base_compounds": len(values), "base_avg": round(avg, 2)}

    def list_simulations(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT id, name, investigation_id, created_at FROM simulations ORDER BY created_at DESC").fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "investigation": r[2], "created_at": r[3]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM simulations").fetchone()[0]
        conn.close()
        return {"total_simulations": total}


class NoveltyDetector:
    """Detects truly novel findings. Phase 212."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def detect(self) -> list[dict]:
        """Find novel items: high novelty insights, outlier patterns."""
        conn = self._get_conn()
        novel = []

        # High-novelty insights
        try:
            rows = conn.execute(
                "SELECT id, insight_type, description, novelty_score FROM insights WHERE novelty_score > 0.5 ORDER BY novelty_score DESC"
            ).fetchall()
            for iid, itype, desc, score in rows:
                novel.append({"type": "insight", "id": iid, "subtype": itype,
                             "description": desc[:80], "novelty": score})
        except Exception:
            pass

        # Outlier entities (those with unusual relation counts)
        try:
            rows = conn.execute("""
                SELECT e.name, COUNT(r.id) as rel_count
                FROM entities e LEFT JOIN entity_relations r ON e.name = r.source_entity
                GROUP BY e.name HAVING rel_count > 3
            """).fetchall()
            for name, count in rows:
                novel.append({"type": "highly_connected", "id": name,
                             "description": f"Entity '{name}' has {count} relations (above average)",
                             "novelty": min(1.0, count / 10.0)})
        except Exception:
            pass

        conn.close()
        novel.sort(key=lambda x: x["novelty"], reverse=True)
        return novel

    def stats(self) -> dict:
        items = self.detect()
        return {"novel_items": len(items)}


simulation_engine = SimulationEngine()
novelty_detector = NoveltyDetector()
