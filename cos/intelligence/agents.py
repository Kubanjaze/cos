"""COS multi-agent system + debate framework. Phase 206-207.

Coordinates multiple reasoning perspectives for stronger conclusions.
"""

import sqlite3
import time
import uuid
import json
from typing import Optional, Callable
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.intelligence.agents")


class Agent:
    """A reasoning agent with a specific perspective."""
    def __init__(self, name: str, perspective: str, analyze_fn: Optional[Callable] = None):
        self.name = name
        self.perspective = perspective
        self._analyze_fn = analyze_fn

    def analyze(self, query: str) -> dict:
        if self._analyze_fn:
            return self._analyze_fn(query)
        return {"agent": self.name, "perspective": self.perspective,
                "analysis": f"Analysis of '{query}' from {self.perspective} perspective",
                "confidence": 0.5}


class MultiAgentSystem:
    """Manages multiple reasoning agents."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._agents: dict[str, Agent] = {}
        self._init_db()
        self._register_builtins()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    agents_used TEXT NOT NULL,
                    consensus TEXT NOT NULL DEFAULT '',
                    debate_rounds INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

    def _register_builtins(self):
        def _optimist(query):
            return {"agent": "optimist", "perspective": "best-case",
                    "analysis": f"Best-case view: '{query}' has strong potential based on available evidence",
                    "confidence": 0.75}

        def _skeptic(query):
            return {"agent": "skeptic", "perspective": "critical",
                    "analysis": f"Critical view: '{query}' needs more evidence before action",
                    "confidence": 0.4}

        def _analyst(query):
            from cos.reasoning.patterns import pattern_detector
            patterns = pattern_detector.stats()
            return {"agent": "analyst", "perspective": "data-driven",
                    "analysis": f"Data view: {patterns['scaffold_patterns']} scaffold patterns, {patterns['entity_types']} entity types",
                    "confidence": 0.65}

        self.register(Agent("optimist", "best-case", _optimist))
        self.register(Agent("skeptic", "critical", _skeptic))
        self.register(Agent("analyst", "data-driven", _analyst))

    def register(self, agent: Agent):
        self._agents[agent.name] = agent

    def consult(self, query: str, agent_names: Optional[list[str]] = None) -> dict:
        """Consult agents and synthesize. Phase 206."""
        agents = agent_names or list(self._agents.keys())
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        results = []

        for name in agents:
            agent = self._agents.get(name)
            if agent:
                results.append(agent.analyze(query))

        # Consensus: average confidence
        if results:
            avg_conf = sum(r["confidence"] for r in results) / len(results)
            consensus = "proceed" if avg_conf >= 0.6 else "needs review"
        else:
            avg_conf, consensus = 0, "no agents"

        rid = f"agt-{uuid.uuid4().hex[:8]}"
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO agent_runs (id, query, agents_used, consensus, created_at) VALUES (?, ?, ?, ?, ?)",
                (rid, query, json.dumps(agents), consensus, ts),
            )

        logger.info(f"Multi-agent consultation: {len(results)} agents, consensus={consensus}")
        return {"run_id": rid, "query": query, "agents": results,
                "consensus": consensus, "avg_confidence": round(avg_conf, 3)}

    def debate(self, query: str, rounds: int = 2) -> dict:
        """Phase 207: Agent debate framework."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        debate_log = []

        for round_num in range(1, rounds + 1):
            round_results = []
            for name, agent in self._agents.items():
                result = agent.analyze(query)
                # Adjust confidence based on previous rounds
                if debate_log:
                    prev_avg = sum(r["confidence"] for r in debate_log[-1]) / len(debate_log[-1])
                    result["confidence"] = round((result["confidence"] + prev_avg) / 2, 3)
                round_results.append(result)
            debate_log.append(round_results)

        # Final consensus after debate
        final = debate_log[-1] if debate_log else []
        avg_conf = sum(r["confidence"] for r in final) / len(final) if final else 0

        rid = f"dbt-{uuid.uuid4().hex[:8]}"
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO agent_runs (id, query, agents_used, consensus, debate_rounds, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (rid, query, json.dumps(list(self._agents.keys())),
                 "proceed" if avg_conf >= 0.6 else "needs review", rounds, ts),
            )

        return {"run_id": rid, "rounds": rounds, "final_confidence": round(avg_conf, 3),
                "debate_log": [[{"agent": r["agent"], "confidence": r["confidence"]} for r in rnd] for rnd in debate_log]}

    def list_agents(self) -> list[dict]:
        return [{"name": a.name, "perspective": a.perspective} for a in self._agents.values()]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0]
        conn.close()
        return {"registered_agents": len(self._agents), "total_runs": total}


multi_agent_system = MultiAgentSystem()
