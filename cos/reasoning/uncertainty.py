"""COS uncertainty estimator — quantify confidence across the system.

Phase 146: Computes uncertainty metrics for concepts, hypotheses, and syntheses.
"""

import sqlite3
import math
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.uncertainty")


class UncertaintyEstimator:
    """Estimates uncertainty across COS knowledge."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def estimate(self, target_type: str, target_id: Optional[str] = None) -> list[dict]:
        """Estimate uncertainty for items of a given type."""
        conn = self._get_conn()
        results = []

        if target_type == "concept":
            if target_id:
                rows = conn.execute(
                    "SELECT id, name, confidence, domain FROM concepts WHERE id=?", (target_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, name, confidence, domain FROM concepts ORDER BY confidence"
                ).fetchall()
            for cid, name, conf, domain in rows:
                uncertainty = round(1.0 - conf, 3)
                entropy = round(-conf * math.log2(max(conf, 0.01)) - (1-conf) * math.log2(max(1-conf, 0.01)), 3)
                results.append({"type": "concept", "id": cid, "name": name, "domain": domain,
                               "confidence": conf, "uncertainty": uncertainty, "entropy": entropy})

        elif target_type == "hypothesis":
            rows = conn.execute(
                "SELECT id, statement, confidence, status FROM hypotheses ORDER BY confidence"
            ).fetchall()
            for hid, stmt, conf, status in rows:
                uncertainty = round(1.0 - conf, 3)
                results.append({"type": "hypothesis", "id": hid, "statement": stmt[:60],
                               "confidence": conf, "uncertainty": uncertainty, "status": status})

        conn.close()
        logger.info(f"Estimated uncertainty for {len(results)} {target_type} items")
        return results

    def system_uncertainty(self) -> dict:
        """Overall system uncertainty report."""
        conn = self._get_conn()
        concept_avg = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM concepts").fetchone()[0]
        concept_min = conn.execute("SELECT COALESCE(MIN(confidence), 0) FROM concepts").fetchone()[0]
        try:
            hyp_avg = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM hypotheses").fetchone()[0]
        except Exception:
            hyp_avg = 0
        entity_avg = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM entities").fetchone()[0]
        conn.close()

        overall = round((concept_avg + entity_avg) / 2, 3) if concept_avg and entity_avg else 0
        return {
            "overall_confidence": overall,
            "overall_uncertainty": round(1 - overall, 3),
            "concept_avg_confidence": round(concept_avg, 3),
            "concept_min_confidence": round(concept_min, 3),
            "hypothesis_avg_confidence": round(hyp_avg, 3),
            "entity_avg_confidence": round(entity_avg, 3),
        }

    def stats(self) -> dict:
        return self.system_uncertainty()


uncertainty_estimator = UncertaintyEstimator()
