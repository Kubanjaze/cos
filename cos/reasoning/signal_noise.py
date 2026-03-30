"""COS signal vs noise classifier — filter what matters. Phase 154."""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.signal_noise")


class SignalNoiseClassifier:
    """Classifies memory items as signal (valuable) or noise (ignorable)."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def classify(self, target_type: str = "entity") -> dict:
        """Classify items as signal or noise based on connectivity and confidence."""
        conn = self._get_conn()
        signal, noise = [], []

        if target_type == "entity":
            rows = conn.execute("""
                SELECT e.id, e.name, e.entity_type, e.confidence,
                       (SELECT COUNT(*) FROM entity_relations r WHERE r.source_entity=e.name) as rel_count
                FROM entities e
            """).fetchall()
            for eid, name, etype, conf, rels in rows:
                item = {"id": eid, "name": name, "type": etype, "confidence": conf, "relations": rels}
                if conf >= 0.7 and rels >= 1:
                    item["classification"] = "signal"
                    item["reason"] = f"High confidence ({conf:.2f}) with {rels} relation(s)"
                    signal.append(item)
                elif conf < 0.3 and rels == 0:
                    item["classification"] = "noise"
                    item["reason"] = f"Low confidence ({conf:.2f}), no relations"
                    noise.append(item)
                else:
                    item["classification"] = "signal"
                    item["reason"] = "Default: moderate confidence/connectivity"
                    signal.append(item)

        elif target_type == "concept":
            rows = conn.execute("SELECT id, name, domain, confidence FROM concepts").fetchall()
            for cid, name, domain, conf in rows:
                item = {"id": cid, "name": name, "domain": domain, "confidence": conf}
                if conf >= 0.5:
                    item["classification"] = "signal"
                    signal.append(item)
                else:
                    item["classification"] = "noise"
                    item["reason"] = f"Low confidence ({conf:.2f})"
                    noise.append(item)

        conn.close()
        logger.info(f"Classified {len(signal)} signal, {len(noise)} noise for {target_type}")
        return {"signal": signal, "noise": noise, "signal_count": len(signal), "noise_count": len(noise),
                "signal_ratio": round(len(signal) / max(1, len(signal) + len(noise)), 3)}

    def stats(self) -> dict:
        entity = self.classify("entity")
        concept = self.classify("concept")
        return {
            "entity_signal": entity["signal_count"], "entity_noise": entity["noise_count"],
            "concept_signal": concept["signal_count"], "concept_noise": concept["noise_count"],
        }


signal_noise_classifier = SignalNoiseClassifier()
