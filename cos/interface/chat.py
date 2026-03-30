"""COS chat interface — context-aware query interface. Phase 197."""

import sqlite3
import time
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.chat")


class ChatInterface:
    """Context-aware chat interface for querying COS."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def query(self, question: str, investigation_id: str = "default") -> dict:
        """Process a natural language query against COS memory."""
        start = time.time()
        results = {"question": question, "answers": [], "sources": []}

        # Route query to appropriate subsystem
        q_lower = question.lower()

        if any(w in q_lower for w in ["what is", "define", "meaning"]):
            results["answers"].extend(self._concept_lookup(q_lower))
        if any(w in q_lower for w in ["how many", "count", "total"]):
            results["answers"].extend(self._count_query(q_lower))
        if any(w in q_lower for w in ["compare", "vs", "versus", "better"]):
            results["answers"].extend(self._comparison_query(q_lower))
        if any(w in q_lower for w in ["risk", "danger", "problem"]):
            results["answers"].extend(self._risk_query())

        # Fallback: hybrid search
        if not results["answers"]:
            from cos.memory.hybrid_query import hybrid_engine
            search_results = hybrid_engine.search(question, top_k=3)
            for r in search_results:
                results["answers"].append({
                    "type": "search_result", "content": r.get("text", ""),
                    "source": f"{r['type']}/{r.get('name', '')}",
                    "confidence": r.get("fused_score", 0),
                })

        results["duration_s"] = round(time.time() - start, 3)
        results["answer_count"] = len(results["answers"])
        return results

    def _concept_lookup(self, query: str) -> list[dict]:
        conn = self._get_conn()
        # Extract likely concept name (last significant word)
        words = [w for w in query.split() if len(w) > 2 and w not in ("what", "is", "the", "define", "meaning", "of")]
        answers = []
        for word in words:
            rows = conn.execute(
                "SELECT name, definition, domain, confidence FROM concepts WHERE name_lower LIKE ?",
                (f"%{word}%",),
            ).fetchall()
            for name, defn, domain, conf in rows:
                answers.append({"type": "concept", "content": f"{name}: {defn}",
                               "source": f"concept/{domain}", "confidence": conf})
        conn.close()
        return answers

    def _count_query(self, query: str) -> list[dict]:
        conn = self._get_conn()
        counts = {}
        for table in ["entities", "concepts", "documents", "decisions", "hypotheses"]:
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                pass
        conn.close()
        content = ", ".join(f"{c} {t}" for t, c in counts.items() if c > 0)
        return [{"type": "count", "content": content, "source": "system", "confidence": 1.0}]

    def _comparison_query(self, query: str) -> list[dict]:
        return [{"type": "suggestion", "content": "Use 'python -m cos reason compare <a> <b>' for detailed comparison",
                 "source": "system", "confidence": 0.5}]

    def _risk_query(self) -> list[dict]:
        conn = self._get_conn()
        try:
            risks = conn.execute("SELECT COUNT(*) FROM risk_assessments").fetchone()[0]
            conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        except Exception:
            risks, conflicts = 0, 0
        conn.close()
        return [{"type": "risk_summary", "content": f"{risks} risk assessments, {conflicts} open conflicts",
                 "source": "system", "confidence": 1.0}]

    def stats(self) -> dict:
        return {"interface": "chat", "mode": "text", "routing_rules": 4}


chat_interface = ChatInterface()
