"""COS LLM-powered chat — Claude API with hard budget cap + caching.

Cost controls:
- Default model: claude-haiku-4-5-20251001 (~$0.001/query)
- Hard budget cap: refuses API calls if spend exceeds limit
- Response cache: same question = cached answer, zero repeat cost
- Max output tokens: 500 per query (~$0.0005/response)
- Full cost tracking in SQLite

Usage:
    from cos.interface.llm_chat import llm_chat
    answer = llm_chat.ask("What should we prioritize for CETP?")
"""

import hashlib
import json
import os
import sqlite3
import time
from typing import Optional

from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.llm_chat")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_BUDGET_USD = 1.00
MAX_OUTPUT_TOKENS = 500

# Haiku pricing (per million tokens)
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
}


class LLMChat:
    """Claude-powered chat with cost controls."""

    def __init__(self, db_path: Optional[str] = None, budget_usd: float = DEFAULT_BUDGET_USD):
        self._db_path = db_path or settings.db_path
        self._budget_usd = budget_usd
        self._model = DEFAULT_MODEL
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_chat_log (
                    id TEXT PRIMARY KEY,
                    question_hash TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    cached INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_hash ON llm_chat_log(question_hash)")

    def _load_api_key(self) -> str:
        """Load API key from .env or environment."""
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.strip().split("=", 1)[1]
        return key

    def _get_total_spend(self) -> float:
        conn = self._get_conn()
        total = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_chat_log").fetchone()[0]
        conn.close()
        return total

    def _check_cache(self, question_hash: str) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT answer FROM llm_chat_log WHERE question_hash=? ORDER BY created_at DESC LIMIT 1",
            (question_hash,),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _gather_context(self) -> str:
        """Gather relevant COS knowledge for the prompt."""
        conn = self._get_conn()
        parts = []

        # Concepts
        try:
            rows = conn.execute(
                "SELECT name, definition, domain, confidence FROM concepts ORDER BY confidence DESC LIMIT 10"
            ).fetchall()
            if rows:
                parts.append("KNOWN CONCEPTS:")
                for name, defn, domain, conf in rows:
                    parts.append(f"  - {name} ({domain}, {conf:.0%} confidence): {defn[:150]}")
        except Exception:
            pass

        # Scaffold activity summary
        try:
            rows = conn.execute("""
                SELECT r1.target_value, COUNT(*),
                       AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL))
                FROM entity_relations r1
                JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
                WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
                AND r2.target_value LIKE 'pIC50=%'
                GROUP BY r1.target_value ORDER BY COUNT(*) DESC
            """).fetchall()
            if rows:
                parts.append("\nSCAFFOLD ACTIVITY DATA:")
                for scaffold, count, avg in rows:
                    parts.append(f"  - {scaffold}: {count} compounds, avg pIC50={avg:.2f}")
        except Exception:
            pass

        # Hypotheses
        try:
            rows = conn.execute(
                "SELECT statement, confidence FROM hypotheses ORDER BY confidence DESC LIMIT 5"
            ).fetchall()
            if rows:
                parts.append("\nCURRENT HYPOTHESES:")
                for stmt, conf in rows:
                    parts.append(f"  - ({conf:.0%}) {stmt[:120]}")
        except Exception:
            pass

        # Decisions
        try:
            rows = conn.execute(
                "SELECT title, recommendation, confidence FROM decisions ORDER BY confidence DESC LIMIT 3"
            ).fetchall()
            if rows:
                parts.append("\nACTIVE DECISIONS:")
                for title, rec, conf in rows:
                    parts.append(f"  - {title} ({conf:.0%}): {rec[:100]}")
        except Exception:
            pass

        # Open conflicts
        try:
            count = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
            if count > 0:
                parts.append(f"\nOPEN CONFLICTS: {count}")
        except Exception:
            pass

        conn.close()
        return "\n".join(parts)

    def ask(self, question: str) -> dict:
        """Ask a question with full cost controls."""
        import uuid
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Hash for cache lookup
        q_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()

        # Check cache first (free)
        cached = self._check_cache(q_hash)
        if cached:
            logger.info(f"LLM chat (cached): {question[:40]}")
            return {
                "answer": cached, "model": self._model, "cached": True,
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "total_spend": self._get_total_spend(), "budget_remaining": self._budget_usd - self._get_total_spend(),
            }

        # Check budget
        total_spend = self._get_total_spend()
        remaining = self._budget_usd - total_spend
        if remaining <= 0:
            return {
                "answer": f"Budget exceeded (${total_spend:.4f} of ${self._budget_usd:.2f} used). "
                          "Increase budget or use cached queries.",
                "model": self._model, "cached": False, "cost_usd": 0.0,
                "budget_exceeded": True, "total_spend": total_spend, "budget_remaining": 0,
            }

        # Load API key
        api_key = self._load_api_key()
        if not api_key:
            return {"answer": "No API key found. Set ANTHROPIC_API_KEY in .env file.",
                    "model": self._model, "cached": False, "cost_usd": 0.0, "error": "no_key"}

        # Gather knowledge context
        context = self._gather_context()

        # Build prompt
        system_prompt = (
            "You are COS, a Cognitive Operating System for drug discovery. "
            "You analyze CETP inhibitor SAR data and provide actionable insights. "
            "Answer concisely based on the knowledge base provided. "
            "Cite specific data points (scaffold names, pIC50 values, compound names) when available. "
            "If you don't have enough data, say so clearly."
        )

        user_message = f"KNOWLEDGE BASE:\n{context}\n\nQUESTION: {question}"

        # Call Claude API
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            answer = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Calculate cost
            pricing = PRICING.get(self._model, PRICING[DEFAULT_MODEL])
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

            # Log to DB
            log_id = f"llm-{uuid.uuid4().hex[:8]}"
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO llm_chat_log (id, question_hash, question, answer, model, input_tokens, output_tokens, cost_usd, cached, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (log_id, q_hash, question, answer, self._model, input_tokens, output_tokens, cost, 0, ts),
                )

            # Learn from answer — store as episodic memory + concept for local reuse
            self._learn_from_answer(question, answer, cost)

            new_total = total_spend + cost
            logger.info(f"LLM chat: {question[:40]} — ${cost:.6f} ({input_tokens}+{output_tokens} tokens)")

            return {
                "answer": answer, "model": self._model, "cached": False,
                "cost_usd": round(cost, 6), "input_tokens": input_tokens, "output_tokens": output_tokens,
                "total_spend": round(new_total, 6), "budget_remaining": round(self._budget_usd - new_total, 4),
            }

        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            return {"answer": f"API error: {str(e)[:200]}", "model": self._model,
                    "cached": False, "cost_usd": 0.0, "error": str(e)[:200]}

    def _learn_from_answer(self, question: str, answer: str, cost: float):
        """Store AI answer in COS memory for local reuse."""
        try:
            # Store as episodic memory
            from cos.memory.episodic import episodic_memory
            episodic_memory.record(
                "llm_analysis", f"AI answered: {question[:80]}",
                input_summary=question[:200],
                output_summary=answer[:200],
                cost_usd=cost,
            )

            # Store as a concept if it looks like a recommendation
            answer_lower = answer.lower()
            if any(w in answer_lower for w in ["recommend", "prioritize", "suggest", "should"]):
                from cos.memory.semantic import semantic_memory
                # Store the Q&A as a concept for local retrieval
                concept_name = f"AI: {question[:60]}"
                semantic_memory.define(
                    concept_name,
                    answer[:500],
                    domain="ai_analysis",
                    category="recommendation",
                    confidence=0.75,
                    source_ref="claude-haiku",
                )
                logger.info(f"Learned concept from AI: {concept_name[:40]}")

        except Exception as e:
            logger.warning(f"Learn from answer failed: {e}")

    def get_spend_summary(self) -> dict:
        """Get spending summary."""
        conn = self._get_conn()
        total = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_chat_log WHERE cached=0").fetchone()[0]
        queries = conn.execute("SELECT COUNT(*) FROM llm_chat_log WHERE cached=0").fetchone()[0]
        cached = conn.execute("SELECT COUNT(*) FROM llm_chat_log WHERE cached=1").fetchone()[0]
        tokens_in = conn.execute("SELECT COALESCE(SUM(input_tokens), 0) FROM llm_chat_log").fetchone()[0]
        tokens_out = conn.execute("SELECT COALESCE(SUM(output_tokens), 0) FROM llm_chat_log").fetchone()[0]
        conn.close()
        return {
            "total_spend": round(total, 6), "budget": self._budget_usd,
            "remaining": round(self._budget_usd - total, 4),
            "api_queries": queries, "cached_queries": cached,
            "total_tokens_in": tokens_in, "total_tokens_out": tokens_out,
            "model": self._model,
        }

    def set_budget(self, amount_usd: float):
        """Update budget cap."""
        self._budget_usd = amount_usd
        logger.info(f"LLM budget set to ${amount_usd:.2f}")


llm_chat = LLMChat()
