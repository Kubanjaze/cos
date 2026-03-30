"""COS missing evidence detector — find what's needed for decisions. Phase 188."""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.decision.missing_evidence")


class MissingEvidenceDetector:
    """Identifies evidence gaps that weaken decisions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def detect(self, decision_id: str) -> list[dict]:
        """Find missing evidence for a specific decision."""
        from cos.decision.schema import decision_store
        dec = decision_store.get(decision_id)
        if not dec:
            return [{"error": "Decision not found"}]

        conn = self._get_conn()
        gaps = []

        # Check: does the decision reference any evidence?
        evidence = dec.evidence_json
        import json
        evidence_list = json.loads(evidence) if evidence else []
        if not evidence_list:
            gaps.append({"type": "no_evidence", "severity": "high",
                        "description": "Decision has no supporting evidence references",
                        "suggestion": "Link hypotheses, concepts, or entities as evidence"})

        # Check: are there low-confidence concepts in the investigation?
        low_conf = conn.execute(
            "SELECT name, confidence FROM concepts WHERE confidence < 0.5 ORDER BY confidence LIMIT 5"
        ).fetchall()
        if low_conf:
            gaps.append({"type": "low_confidence_knowledge", "severity": "medium",
                        "description": f"{len(low_conf)} concept(s) below 0.5 confidence",
                        "items": [{"name": n, "confidence": c} for n, c in low_conf],
                        "suggestion": "Verify or improve low-confidence concepts"})

        # Check: are there unlinked entities?
        unlinked = conn.execute("""
            SELECT COUNT(*) FROM entities e
            LEFT JOIN entity_relations r ON e.name = r.source_entity
            WHERE r.id IS NULL
        """).fetchone()[0]
        if unlinked > 0:
            gaps.append({"type": "unlinked_entities", "severity": "low",
                        "description": f"{unlinked} entities with no relations",
                        "suggestion": "Extract relations for isolated entities"})

        conn.close()
        logger.info(f"Found {len(gaps)} evidence gaps for decision {decision_id}")
        return gaps

    def detect_global(self) -> list[dict]:
        """Find system-wide evidence gaps."""
        conn = self._get_conn()
        gaps = []

        # Sparse domains
        rows = conn.execute("SELECT domain, COUNT(*) FROM concepts GROUP BY domain HAVING COUNT(*) < 3").fetchall()
        for domain, cnt in rows:
            gaps.append({"type": "sparse_domain", "domain": domain, "count": cnt,
                        "suggestion": f"Add more concepts to '{domain}' domain"})

        # Decisions without risk assessment
        try:
            no_risk = conn.execute("""
                SELECT d.id, d.title FROM decisions d
                LEFT JOIN risk_assessments r ON d.id = r.decision_id
                WHERE r.id IS NULL
            """).fetchall()
            for did, title in no_risk:
                gaps.append({"type": "unassessed_risk", "decision": did,
                            "title": title[:40], "suggestion": "Run risk assessment"})
        except Exception:
            pass

        conn.close()
        return gaps

    def stats(self) -> dict:
        gaps = self.detect_global()
        return {"total_gaps": len(gaps), "by_type": {}}


missing_evidence_detector = MissingEvidenceDetector()
