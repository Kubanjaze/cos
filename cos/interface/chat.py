"""COS chat interface — context-aware query interface. Phase 197."""

import sqlite3
import time
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.chat")

SCAFFOLD_NAMES = {"benz", "naph", "ind", "quin", "pyr", "bzim"}
STOP_WORDS = {"what", "is", "the", "define", "meaning", "of", "tell", "me", "about",
              "show", "find", "get", "list", "how", "many", "which", "are", "there",
              "can", "you", "does", "should", "study", "know", "give"}


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
        q_lower = question.lower().strip()

        # Route 1: Concept/definition lookup
        if any(w in q_lower for w in ["what is", "define", "meaning", "tell me about", "describe", "explain"]):
            results["answers"].extend(self._concept_lookup(q_lower))

        # Route 2: Scaffold-specific queries
        for scaffold in SCAFFOLD_NAMES:
            if scaffold in q_lower:
                results["answers"].extend(self._scaffold_query(scaffold))
                break

        # Route 3: Compound-specific queries
        if "_" in question and any(s in q_lower for s in SCAFFOLD_NAMES):
            results["answers"].extend(self._compound_query(q_lower))

        # Route 4: Activity / potency / SAR queries
        if any(w in q_lower for w in ["activity", "potency", "pic50", "ic50", "sar", "active", "potent", "best", "top", "strongest"]):
            results["answers"].extend(self._activity_query(q_lower))

        # Route 5: Count queries
        if any(w in q_lower for w in ["how many", "count", "total", "number of"]):
            results["answers"].extend(self._count_query(q_lower))

        # Route 6: Comparison queries
        if any(w in q_lower for w in ["compare", "vs", "versus", "better", "difference"]):
            results["answers"].extend(self._comparison_query(q_lower))

        # Route 7: Risk / conflict queries
        if any(w in q_lower for w in ["risk", "danger", "problem", "conflict", "issue", "concern"]):
            results["answers"].extend(self._risk_query())

        # Route 8: Hypothesis / insight queries
        if any(w in q_lower for w in ["hypothesis", "hypotheses", "insight", "finding", "discover", "pattern"]):
            results["answers"].extend(self._hypothesis_query())

        # Route 9: System / overview queries
        if any(w in q_lower for w in ["overview", "summary", "status", "system", "dashboard"]):
            results["answers"].extend(self._overview_query())

        # Route 10: Help / what can you do
        if any(w in q_lower for w in ["help", "what can", "how do i", "guide", "tutorial"]):
            results["answers"].extend(self._help_query())

        # Fallback: hybrid search on meaningful words
        if not results["answers"]:
            from cos.memory.hybrid_query import hybrid_engine
            search_results = hybrid_engine.search(question, top_k=5)
            for r in search_results:
                results["answers"].append({
                    "type": "search_result", "content": r.get("text", ""),
                    "source": f"{r['type']}/{r.get('name', '')}",
                    "confidence": r.get("fused_score", 0),
                })

        # Ultimate fallback: suggest what to ask
        if not results["answers"]:
            results["answers"].append({
                "type": "suggestion",
                "content": "I don't have data matching that query. Try asking about: CETP, scaffolds (benz/naph/ind/quin/pyr/bzim), compound activity, hypotheses, or system overview.",
                "source": "system", "confidence": 1.0,
            })

        results["duration_s"] = round(time.time() - start, 3)
        results["answer_count"] = len(results["answers"])
        return results

    def _concept_lookup(self, query: str) -> list[dict]:
        conn = self._get_conn()
        words = [w for w in query.split() if len(w) > 2 and w not in STOP_WORDS]
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

    def _scaffold_query(self, scaffold: str) -> list[dict]:
        """Query scaffold family details."""
        conn = self._get_conn()
        answers = []

        # Count compounds in scaffold
        count = conn.execute(
            "SELECT COUNT(*) FROM entity_relations WHERE relation_type='belongs_to_scaffold' AND target_value=?",
            (scaffold,),
        ).fetchone()[0]

        # Get activity data
        rows = conn.execute("""
            SELECT r2.source_entity, r2.target_value
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            WHERE r1.relation_type='belongs_to_scaffold' AND r1.target_value=?
            AND r2.relation_type='has_activity' AND r2.target_value LIKE 'pIC50=%'
            ORDER BY r2.target_value DESC
        """, (scaffold,)).fetchall()

        compounds_with_activity = []
        for comp, act in rows:
            try:
                val = float(act.replace("pIC50=", ""))
                compounds_with_activity.append((comp, val))
            except ValueError:
                pass

        if compounds_with_activity:
            avg = sum(v for _, v in compounds_with_activity) / len(compounds_with_activity)
            best = max(compounds_with_activity, key=lambda x: x[1])
            worst = min(compounds_with_activity, key=lambda x: x[1])

            answers.append({
                "type": "scaffold_profile",
                "content": f"Scaffold '{scaffold}': {count} compounds, {len(compounds_with_activity)} with activity data. "
                          f"Avg pIC50={avg:.2f}, Best: {best[0]} (pIC50={best[1]:.2f}), "
                          f"Weakest: {worst[0]} (pIC50={worst[1]:.2f})",
                "source": f"scaffold/{scaffold}", "confidence": 0.95,
            })

            # List top compounds
            top_3 = sorted(compounds_with_activity, key=lambda x: x[1], reverse=True)[:3]
            compounds_str = ", ".join(f"{c} (pIC50={v:.2f})" for c, v in top_3)
            answers.append({
                "type": "top_compounds",
                "content": f"Top compounds in {scaffold}: {compounds_str}",
                "source": f"scaffold/{scaffold}", "confidence": 0.9,
            })
        else:
            answers.append({
                "type": "scaffold_info",
                "content": f"Scaffold '{scaffold}': {count} compounds. No activity data extracted yet.",
                "source": f"scaffold/{scaffold}", "confidence": 0.7,
            })

        conn.close()
        return answers

    def _compound_query(self, query: str) -> list[dict]:
        """Look up a specific compound."""
        conn = self._get_conn()
        answers = []

        # Find compound name in query
        words = query.split()
        for word in words:
            if "_" in word:
                rows = conn.execute(
                    "SELECT name, entity_type, confidence FROM entities WHERE name LIKE ?",
                    (f"%{word}%",),
                ).fetchall()
                for name, etype, conf in rows:
                    # Get activity
                    act_row = conn.execute(
                        "SELECT target_value FROM entity_relations WHERE source_entity=? AND relation_type='has_activity'",
                        (name,),
                    ).fetchone()
                    # Get scaffold
                    scaf_row = conn.execute(
                        "SELECT target_value FROM entity_relations WHERE source_entity=? AND relation_type='belongs_to_scaffold'",
                        (name,),
                    ).fetchone()

                    activity = act_row[0] if act_row else "no data"
                    scaffold = scaf_row[0] if scaf_row else "unknown"

                    answers.append({
                        "type": "compound",
                        "content": f"{name}: {etype}, scaffold={scaffold}, activity={activity}",
                        "source": f"entity/{name}", "confidence": conf,
                    })

        conn.close()
        return answers

    def _activity_query(self, query: str) -> list[dict]:
        """Query about activity / most potent compounds."""
        conn = self._get_conn()
        answers = []

        rows = conn.execute("""
            SELECT r.source_entity, r.target_value, r2.target_value as scaffold
            FROM entity_relations r
            JOIN entity_relations r2 ON r.source_entity = r2.source_entity AND r2.relation_type='belongs_to_scaffold'
            WHERE r.relation_type='has_activity' AND r.target_value LIKE 'pIC50=%'
            ORDER BY CAST(REPLACE(r.target_value, 'pIC50=', '') AS REAL) DESC
        """).fetchall()

        if rows:
            # Parse and rank
            ranked = []
            for comp, act, scaffold in rows:
                try:
                    val = float(act.replace("pIC50=", ""))
                    ranked.append((comp, val, scaffold))
                except ValueError:
                    pass

            if ranked:
                top5 = ranked[:5]
                content = "Most potent compounds:\n" + "\n".join(
                    f"  {i+1}. {c} (pIC50={v:.2f}, scaffold={s})" for i, (c, v, s) in enumerate(top5)
                )
                answers.append({
                    "type": "activity_ranking",
                    "content": content,
                    "source": "entity_relations/activity", "confidence": 0.95,
                })

                # Summary by scaffold
                from collections import defaultdict
                by_scaffold = defaultdict(list)
                for c, v, s in ranked:
                    by_scaffold[s].append(v)

                scaffold_summary = ", ".join(
                    f"{s}: avg={sum(vs)/len(vs):.2f} ({len(vs)} compounds)"
                    for s, vs in sorted(by_scaffold.items(), key=lambda x: -sum(x[1])/len(x[1]))
                )
                answers.append({
                    "type": "scaffold_ranking",
                    "content": f"Activity by scaffold: {scaffold_summary}",
                    "source": "entity_relations/scaffold", "confidence": 0.9,
                })

        conn.close()
        return answers

    def _count_query(self, query: str) -> list[dict]:
        conn = self._get_conn()
        counts = {}
        for table, label in [("entities", "entities"), ("concepts", "concepts"),
                              ("documents", "documents"), ("decisions", "decisions"),
                              ("hypotheses", "hypotheses"), ("entity_relations", "relations"),
                              ("provenance", "provenance links")]:
            try:
                counts[label] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                pass
        conn.close()
        content = "System contains: " + ", ".join(f"{c} {t}" for t, c in counts.items() if c > 0)
        return [{"type": "count", "content": content, "source": "system", "confidence": 1.0}]

    def _comparison_query(self, query: str) -> list[dict]:
        """Compare two scaffolds if mentioned."""
        found = [s for s in SCAFFOLD_NAMES if s in query.lower()]
        if len(found) >= 2:
            from cos.reasoning.comparison import comparison_engine
            result = comparison_engine.compare_scaffolds(found[0], found[1])
            a, b = result["a"], result["b"]
            return [{"type": "comparison",
                     "content": f"{a['scaffold']}: {a['compounds']} compounds, avg pIC50={a['avg_pIC50']} vs "
                               f"{b['scaffold']}: {b['compounds']} compounds, avg pIC50={b['avg_pIC50']}. "
                               f"Winner: {result['winner']} (margin={result['margin']} pIC50 units)",
                     "source": "reasoning/comparison", "confidence": 0.9}]
        return [{"type": "suggestion",
                "content": "Name two scaffolds to compare (benz, naph, ind, quin, pyr, bzim). Example: 'compare benz vs ind'",
                "source": "system", "confidence": 0.8}]

    def _risk_query(self) -> list[dict]:
        conn = self._get_conn()
        answers = []
        try:
            risks = conn.execute("SELECT COUNT(*) FROM risk_assessments").fetchone()[0]
            conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
            low_conf = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
            answers.append({"type": "risk_summary",
                           "content": f"System risks: {risks} risk assessment(s), {conflicts} open conflict(s), {low_conf} low-confidence concept(s)",
                           "source": "system", "confidence": 1.0})
        except Exception:
            pass
        conn.close()
        return answers

    def _hypothesis_query(self) -> list[dict]:
        conn = self._get_conn()
        answers = []
        try:
            rows = conn.execute(
                "SELECT statement, confidence, status FROM hypotheses ORDER BY confidence DESC LIMIT 3"
            ).fetchall()
            if rows:
                hyp_list = "\n".join(f"  - ({conf:.0%}) {stmt[:80]}" for stmt, conf, status in rows)
                answers.append({"type": "hypotheses",
                               "content": f"Top hypotheses:\n{hyp_list}",
                               "source": "reasoning/hypotheses", "confidence": 0.85})

            # Insights
            rows = conn.execute(
                "SELECT description, novelty_score FROM insights ORDER BY novelty_score DESC LIMIT 3"
            ).fetchall()
            if rows:
                insight_list = "\n".join(f"  - (novelty={ns:.0%}) {desc[:80]}" for desc, ns in rows)
                answers.append({"type": "insights",
                               "content": f"Key insights:\n{insight_list}",
                               "source": "reasoning/insights", "confidence": 0.8})
        except Exception:
            pass
        conn.close()
        return answers

    def _overview_query(self) -> list[dict]:
        conn = self._get_conn()
        answers = []
        try:
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
            concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
            hypotheses = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
            decisions = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

            answers.append({"type": "overview",
                           "content": f"COS Knowledge Base: {entities} entities, {relations} relations, "
                                     f"{concepts} concepts, {hypotheses} hypotheses, {decisions} decisions. "
                                     f"Domain: CETP inhibitor SAR analysis with 6 scaffold families.",
                           "source": "system", "confidence": 1.0})
        except Exception:
            pass
        conn.close()
        return answers

    def _help_query(self) -> list[dict]:
        return [{"type": "help",
                "content": "You can ask me about:\n"
                          "  - Compounds: 'tell me about benz_001_F'\n"
                          "  - Scaffolds: 'tell me about the benz scaffold'\n"
                          "  - Activity: 'what are the most potent compounds?'\n"
                          "  - Comparisons: 'compare benz vs ind'\n"
                          "  - Concepts: 'what is CETP?'\n"
                          "  - Hypotheses: 'show me hypotheses'\n"
                          "  - Counts: 'how many entities are there?'\n"
                          "  - Risks: 'are there any risks?'\n"
                          "  - Overview: 'give me a system overview'",
                "source": "system", "confidence": 1.0}]

    def get_suggested_queries(self) -> list[str]:
        """Return suggested queries for the UI."""
        return [
            "What is CETP?",
            "Tell me about the ind scaffold",
            "What are the most potent compounds?",
            "Compare benz vs ind",
            "Show me hypotheses",
            "How many entities are there?",
            "Are there any risks?",
            "Give me a system overview",
        ]

    def stats(self) -> dict:
        return {"interface": "chat", "mode": "text", "routing_rules": 10}


chat_interface = ChatInterface()
