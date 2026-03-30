"""COS insight extraction — identify what's actually new. Phase 153."""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.insights")


class InsightExtractor:
    """Extracts novel insights from analysis results."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    insight_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    novelty_score REAL NOT NULL DEFAULT 0.5,
                    investigation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
            """)

    def extract(self, investigation_id: str = "default") -> list[dict]:
        """Extract insights from current knowledge state."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        insights = []

        # Insight: scaffolds with unusually high/low activity
        rows = conn.execute("""
            SELECT r1.target_value as scaffold, AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg_act,
                   COUNT(*) as cnt
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
            AND r2.target_value LIKE 'pIC50=%'
            GROUP BY scaffold HAVING cnt >= 2
        """).fetchall()

        if rows:
            overall_avg = sum(r[1] for r in rows) / len(rows)
            for scaffold, avg_act, cnt in rows:
                if abs(avg_act - overall_avg) > 0.5:
                    direction = "above" if avg_act > overall_avg else "below"
                    iid = f"ins-{uuid.uuid4().hex[:8]}"
                    desc = f"Scaffold '{scaffold}' avg pIC50={avg_act:.2f} is {abs(avg_act - overall_avg):.2f} {direction} overall mean ({overall_avg:.2f})"
                    novelty = min(1.0, abs(avg_act - overall_avg) / 2.0)
                    conn.execute(
                        "INSERT OR IGNORE INTO insights (id, insight_type, description, evidence_json, novelty_score, investigation_id, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (iid, "activity_outlier", desc, json.dumps({"scaffold": scaffold, "avg": round(avg_act, 2), "overall": round(overall_avg, 2)}),
                         novelty, investigation_id, ts),
                    )
                    insights.append({"id": iid, "type": "activity_outlier", "description": desc, "novelty": round(novelty, 3)})

        # Insight: sparse domains
        rows = conn.execute("SELECT domain, COUNT(*) FROM concepts GROUP BY domain HAVING COUNT(*) < 3").fetchall()
        for domain, cnt in rows:
            iid = f"ins-{uuid.uuid4().hex[:8]}"
            desc = f"Domain '{domain}' has only {cnt} concept(s) — potential knowledge gap"
            conn.execute(
                "INSERT OR IGNORE INTO insights (id, insight_type, description, evidence_json, novelty_score, investigation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (iid, "knowledge_gap", desc, json.dumps({"domain": domain, "count": cnt}), 0.6, investigation_id, ts),
            )
            insights.append({"id": iid, "type": "knowledge_gap", "description": desc, "novelty": 0.6})

        conn.commit()
        conn.close()
        logger.info(f"Extracted {len(insights)} insights")
        return insights

    def list_insights(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT id, insight_type, description, novelty_score, created_at FROM insights ORDER BY novelty_score DESC").fetchall()
        conn.close()
        return [{"id": r[0], "type": r[1], "description": r[2], "novelty": r[3], "created_at": r[4]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
        by_type = conn.execute("SELECT insight_type, COUNT(*) FROM insights GROUP BY insight_type").fetchall()
        conn.close()
        return {"total": total, "by_type": {t: c for t, c in by_type}}


insight_extractor = InsightExtractor()
