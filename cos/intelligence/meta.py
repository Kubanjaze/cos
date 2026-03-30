"""COS autonomous hypothesis loop + meta-reasoning. Phase 213-214.

Also covers: Phase 215 (intelligence benchmark suite).
"""

import sqlite3
import time
import uuid
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.intelligence.meta")


class AutonomousHypothesisLoop:
    """Generates, tests, and refines hypotheses autonomously. Phase 213."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def run_cycle(self, investigation_id: str = "default") -> dict:
        """Run one autonomous hypothesis cycle: generate → challenge → refine."""
        from cos.reasoning.hypothesis import hypothesis_generator
        from cos.reasoning.disconfirmation import disconfirmation_engine
        from cos.reasoning.refinement import refinement_loop

        start = time.time()
        results = {"steps": []}

        # Step 1: Generate hypotheses
        hyps = hypothesis_generator.generate(investigation_id=investigation_id)
        results["steps"].append({"action": "generate", "hypotheses": len(hyps)})

        # Step 2: Challenge each
        challenges = []
        for h in hyps:
            c = disconfirmation_engine.challenge(h["id"])
            challenges.append(c)
        results["steps"].append({"action": "challenge", "challenged": len(challenges)})

        # Step 3: Refine survivors
        refined = 0
        for h in hyps:
            try:
                refinement_loop.refine_hypothesis(h["id"])
                refined += 1
            except Exception:
                pass
        results["steps"].append({"action": "refine", "refined": refined})

        results["duration_s"] = round(time.time() - start, 3)
        results["cycle_complete"] = True
        logger.info(f"Autonomous cycle: {len(hyps)} generated, {len(challenges)} challenged, {refined} refined")
        return results


class MetaReasoner:
    """Reasons about the reasoning process itself. Phase 214."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def assess_reasoning_quality(self) -> dict:
        """Assess how well the reasoning system is performing."""
        conn = self._get_conn()
        metrics = {}

        # Hypothesis quality
        try:
            total_hyps = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
            avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM hypotheses").fetchone()[0]
            metrics["hypothesis_count"] = total_hyps
            metrics["hypothesis_avg_confidence"] = round(avg_conf, 3)
        except Exception:
            metrics["hypothesis_count"] = 0

        # Reasoning coverage
        try:
            syntheses = conn.execute("SELECT COUNT(*) FROM syntheses").fetchone()[0]
            insights = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
            metrics["syntheses"] = syntheses
            metrics["insights"] = insights
        except Exception:
            pass

        # Decision quality
        try:
            decisions = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            dec_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0) FROM decisions").fetchone()[0]
            metrics["decisions"] = decisions
            metrics["decision_avg_confidence"] = round(dec_conf, 3)
        except Exception:
            pass

        # Meta-assessment
        coverage = min(1.0, (metrics.get("syntheses", 0) + metrics.get("insights", 0)) / 10)
        quality = metrics.get("hypothesis_avg_confidence", 0)
        actionability = min(1.0, metrics.get("decisions", 0) / 5)

        metrics["meta_score"] = round(0.4 * quality + 0.3 * coverage + 0.3 * actionability, 3)
        metrics["recommendations"] = []

        if quality < 0.6:
            metrics["recommendations"].append("Improve hypothesis confidence through more evidence")
        if coverage < 0.5:
            metrics["recommendations"].append("Run more syntheses and insight extractions")
        if actionability < 0.5:
            metrics["recommendations"].append("Generate more decisions from reasoning outputs")

        conn.close()
        return metrics

    def suggest_next_actions(self) -> list[str]:
        """Suggest what the system should do next."""
        assessment = self.assess_reasoning_quality()
        actions = assessment.get("recommendations", [])
        if not actions:
            actions.append("System is performing well — continue current approach")
        return actions


class IntelligenceBenchmark:
    """Intelligence benchmark suite. Phase 215."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_benchmarks (
                    id TEXT PRIMARY KEY,
                    reasoning_score REAL NOT NULL,
                    decision_score REAL NOT NULL,
                    memory_coverage REAL NOT NULL,
                    meta_score REAL NOT NULL,
                    composite REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def run(self) -> dict:
        """Run full intelligence benchmark."""
        conn = self._get_conn()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Reasoning score
        try:
            from cos.reasoning.benchmark import reasoning_benchmark
            r_bench = reasoning_benchmark.run_benchmark("intelligence-check")
            reasoning_score = r_bench["composite"]
        except Exception:
            reasoning_score = 0

        # Decision score
        try:
            from cos.decision.benchmark import decision_benchmark
            d_bench = decision_benchmark.run()
            decision_score = d_bench["composite"]
        except Exception:
            decision_score = 0

        # Memory coverage
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        memory_coverage = min(1.0, (entities + concepts + relations) / 200)

        # Meta-reasoning
        meta = MetaReasoner(self._db_path)
        meta_result = meta.assess_reasoning_quality()
        meta_score = meta_result.get("meta_score", 0)

        # Composite
        composite = round(0.3 * reasoning_score + 0.25 * decision_score +
                         0.25 * memory_coverage + 0.2 * meta_score, 4)

        bid = f"ibench-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO intelligence_benchmarks (id, reasoning_score, decision_score, memory_coverage, meta_score, composite, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bid, reasoning_score, decision_score, memory_coverage, meta_score, composite, ts),
        )
        conn.commit()
        conn.close()

        logger.info(f"Intelligence benchmark: composite={composite}")
        return {
            "id": bid, "composite": composite,
            "reasoning": round(reasoning_score, 4), "decision": round(decision_score, 4),
            "memory": round(memory_coverage, 4), "meta": round(meta_score, 4),
        }

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM intelligence_benchmarks").fetchone()[0]
        latest = conn.execute("SELECT composite FROM intelligence_benchmarks ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        return {"total_runs": total, "latest_composite": latest[0] if latest else None}


autonomous_loop = AutonomousHypothesisLoop()
meta_reasoner = MetaReasoner()
intelligence_benchmark = IntelligenceBenchmark()
