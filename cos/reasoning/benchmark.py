"""COS reasoning benchmark suite — measure system improvement. Phase 160.

Implements ADR-005 tri-metric evaluation: Quality (40%) + Cost (40%) + Latency (20%).
"""

import time
import sqlite3
import json
import uuid
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.benchmark")


class ReasoningBenchmark:
    """Benchmarks reasoning quality, cost, and latency per ADR-005."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    latency_p95_s REAL NOT NULL DEFAULT 0,
                    composite_score REAL NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)

    def run_benchmark(self, name: str = "full") -> dict:
        """Run the reasoning benchmark suite."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        start = time.time()
        details = {}

        # Quality: measure coverage and consistency
        quality = self._measure_quality(details)

        # Cost: measure total API spend
        cost = self._measure_cost(details)

        # Latency: measure operation speed
        latency = self._measure_latency(details)

        # ADR-005 composite: Quality 40% + Cost 40% + Latency 20%
        # Normalize cost (lower is better): cost_score = max(0, 1 - cost/1.0)
        cost_score = max(0.0, 1.0 - cost)
        # Normalize latency (lower is better): latency_score = max(0, 1 - latency/10.0)
        latency_score = max(0.0, 1.0 - latency / 10.0)

        composite = round(0.4 * quality + 0.4 * cost_score + 0.2 * latency_score, 4)

        bid = f"bench-{uuid.uuid4().hex[:8]}"
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO benchmark_runs (id, name, quality_score, cost_usd, latency_p95_s, composite_score, details_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (bid, name, quality, cost, latency, composite, json.dumps(details), ts),
            )

        result = {
            "id": bid, "name": name,
            "quality": round(quality, 4), "cost_usd": round(cost, 4),
            "latency_p95_s": round(latency, 3), "composite": composite,
            "scorecard": {"quality_40pct": round(0.4 * quality, 4),
                         "cost_40pct": round(0.4 * cost_score, 4),
                         "latency_20pct": round(0.2 * latency_score, 4)},
            "duration_s": round(time.time() - start, 3),
        }

        logger.info(f"Benchmark '{name}': composite={composite}, quality={quality:.3f}, cost=${cost:.4f}, latency={latency:.3f}s")
        return result

    def _measure_quality(self, details: dict) -> float:
        """Quality = coverage (entities+concepts+relations) normalized."""
        conn = self._get_conn()
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        provenance = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
        conn.close()

        # Quality heuristic: more connected knowledge = higher quality
        coverage = min(1.0, (entities + concepts + relations) / 200)
        provenance_ratio = min(1.0, provenance / max(1, entities + relations))
        quality = round(0.6 * coverage + 0.4 * provenance_ratio, 4)

        details["quality"] = {"entities": entities, "concepts": concepts, "relations": relations,
                              "provenance": provenance, "coverage": coverage, "provenance_ratio": round(provenance_ratio, 3)}
        return quality

    def _measure_cost(self, details: dict) -> float:
        """Total API cost in USD."""
        conn = self._get_conn()
        cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events").fetchone()[0]
        conn.close()
        details["cost"] = {"total_usd": round(cost, 4)}
        return cost

    def _measure_latency(self, details: dict) -> float:
        """Latency: time to run a synthesis query."""
        start = time.time()
        from cos.reasoning.synthesis import synthesis_engine
        synthesis_engine.synthesize("benchmark_test", investigation_id="benchmark")
        latency = time.time() - start
        details["latency"] = {"synthesis_s": round(latency, 3)}
        return latency

    def list_runs(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, quality_score, cost_usd, latency_p95_s, composite_score, created_at "
            "FROM benchmark_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "quality": r[2], "cost": r[3],
                 "latency": r[4], "composite": r[5], "created_at": r[6]} for r in rows]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM benchmark_runs").fetchone()[0]
        latest = conn.execute(
            "SELECT composite_score, quality_score, cost_usd, latency_p95_s FROM benchmark_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if latest:
            return {"total_runs": total, "latest_composite": latest[0], "latest_quality": latest[1],
                    "latest_cost": latest[2], "latest_latency": latest[3]}
        return {"total_runs": 0}


reasoning_benchmark = ReasoningBenchmark()
