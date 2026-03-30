"""COS disconfirmation engine — challenge hypotheses with counter-evidence.

Phase 145: Tests hypotheses against available evidence to find weaknesses.
"""

import sqlite3
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.disconfirmation")


class DisconfirmationEngine:
    """Challenges hypotheses with counter-evidence."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def challenge(self, hypothesis_id: str) -> dict:
        """Find counter-evidence for a hypothesis."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, statement, evidence_json, confidence FROM hypotheses WHERE id=?",
            (hypothesis_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"error": f"Hypothesis not found: {hypothesis_id}"}

        hid, statement, evidence_str, confidence = row
        evidence = json.loads(evidence_str)
        challenges = []

        # Check for contradictory relations
        for ev in evidence:
            scaffold = ev.get("scaffold")
            if scaffold:
                # Look for outlier activities (low pIC50 in otherwise active scaffold)
                rows = conn.execute("""
                    SELECT source_entity, target_value FROM entity_relations
                    WHERE relation_type='has_activity' AND source_entity IN
                    (SELECT source_entity FROM entity_relations WHERE relation_type='belongs_to_scaffold' AND target_value=?)
                """, (scaffold,)).fetchall()
                vals = []
                for comp, act in rows:
                    if "pIC50=" in act:
                        try:
                            vals.append((comp, float(act.replace("pIC50=", ""))))
                        except ValueError:
                            pass
                if vals:
                    avg = sum(v for _, v in vals) / len(vals)
                    outliers = [(c, v) for c, v in vals if abs(v - avg) > 1.0]
                    if outliers:
                        challenges.append({
                            "type": "outlier_activity",
                            "detail": f"{len(outliers)} compounds deviate >1 pIC50 unit from mean",
                            "examples": [{"compound": c, "pIC50": v} for c, v in outliers[:3]],
                        })

        # Check for open conflicts related to hypothesis entities
        conflict_count = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        if conflict_count > 0:
            challenges.append({
                "type": "unresolved_conflicts",
                "detail": f"{conflict_count} open conflicts may affect hypothesis validity",
            })

        conn.close()

        new_confidence = confidence * (0.9 ** len(challenges)) if challenges else confidence
        logger.info(f"Challenged hypothesis {hid}: {len(challenges)} issues found")

        return {
            "hypothesis_id": hid, "statement": statement,
            "original_confidence": confidence,
            "challenges": challenges, "challenge_count": len(challenges),
            "adjusted_confidence": round(new_confidence, 3),
        }

    def challenge_all(self) -> list[dict]:
        """Challenge all proposed hypotheses."""
        conn = self._get_conn()
        rows = conn.execute("SELECT id FROM hypotheses WHERE status='proposed'").fetchall()
        conn.close()
        return [self.challenge(r[0]) for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
        proposed = conn.execute("SELECT COUNT(*) FROM hypotheses WHERE status='proposed'").fetchone()[0]
        conn.close()
        return {"total_hypotheses": total, "proposed": proposed}


disconfirmation_engine = DisconfirmationEngine()
