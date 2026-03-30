"""COS decision quality benchmark — are decisions improving? Phase 195."""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.benchmark")


class DecisionBenchmark:
    """Benchmarks decision quality over time."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_benchmarks (
                    id TEXT PRIMARY KEY,
                    total_decisions INTEGER NOT NULL,
                    avg_confidence REAL NOT NULL,
                    decisions_with_risks INTEGER NOT NULL,
                    decisions_with_evidence INTEGER NOT NULL,
                    outcome_accuracy REAL NOT NULL DEFAULT 0,
                    composite_score REAL NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)

    def run(self) -> dict:
        """Run decision quality benchmark."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM decisions").fetchone()[0]

        # Decisions with risk assessments
        with_risks = conn.execute("""
            SELECT COUNT(DISTINCT d.id) FROM decisions d
            JOIN risk_assessments r ON d.id = r.decision_id
        """).fetchone()[0]

        # Decisions with evidence
        import json as _json
        rows = conn.execute("SELECT evidence_json FROM decisions").fetchall()
        with_evidence = sum(1 for r in rows if _json.loads(r[0]))

        # Outcome accuracy
        try:
            outcomes = conn.execute("SELECT COUNT(*) FROM decision_outcomes").fetchone()[0]
            correct = conn.execute("SELECT COUNT(*) FROM decision_outcomes WHERE outcome_type='correct'").fetchone()[0]
            accuracy = correct / max(1, outcomes)
        except Exception:
            accuracy = 0

        # Composite: evidence_coverage * 0.3 + risk_coverage * 0.3 + confidence * 0.2 + accuracy * 0.2
        ev_ratio = with_evidence / max(1, total)
        risk_ratio = with_risks / max(1, total)
        composite = round(0.3 * ev_ratio + 0.3 * risk_ratio + 0.2 * avg_conf + 0.2 * accuracy, 4)

        bid = f"dbench-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO decision_benchmarks (id, total_decisions, avg_confidence, decisions_with_risks, "
            "decisions_with_evidence, outcome_accuracy, composite_score, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (bid, total, avg_conf, with_risks, with_evidence, accuracy, composite,
             json.dumps({"ev_ratio": ev_ratio, "risk_ratio": risk_ratio}), ts),
        )
        conn.commit()
        conn.close()

        result = {
            "id": bid, "total_decisions": total, "avg_confidence": round(avg_conf, 3),
            "with_risks": with_risks, "with_evidence": with_evidence,
            "outcome_accuracy": round(accuracy, 3), "composite": composite,
            "breakdown": {"evidence_30pct": round(0.3 * ev_ratio, 4),
                         "risk_30pct": round(0.3 * risk_ratio, 4),
                         "confidence_20pct": round(0.2 * avg_conf, 4),
                         "accuracy_20pct": round(0.2 * accuracy, 4)},
        }
        logger.info(f"Decision benchmark: composite={composite}")
        return result

    def history(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, total_decisions, composite_score, created_at FROM decision_benchmarks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [{"id": r[0], "decisions": r[1], "composite": r[2], "created_at": r[3]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM decision_benchmarks").fetchone()[0]
        latest = conn.execute("SELECT composite_score FROM decision_benchmarks ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        return {"total_runs": total, "latest_composite": latest[0] if latest else None}


decision_benchmark = DecisionBenchmark()
