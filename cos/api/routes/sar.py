"""COS API — SAR analysis routes (scaffold profiles, comparisons, heatmap)."""

import sqlite3
from fastapi import APIRouter
from cos.core.config import settings

router = APIRouter()


@router.get("/sar/scaffolds")
def scaffold_profiles():
    """Full SAR profile for each scaffold family."""
    conn = sqlite3.connect(settings.db_path)
    scaffolds = conn.execute(
        "SELECT DISTINCT target_value FROM entity_relations WHERE relation_type='belongs_to_scaffold' ORDER BY target_value"
    ).fetchall()

    profiles = []
    for (scaffold,) in scaffolds:
        # Get compounds + activity
        rows = conn.execute("""
            SELECT r1.source_entity, r2.target_value
            FROM entity_relations r1
            LEFT JOIN entity_relations r2 ON r1.source_entity = r2.source_entity AND r2.relation_type='has_activity'
            WHERE r1.relation_type='belongs_to_scaffold' AND r1.target_value=?
            ORDER BY r1.source_entity
        """, (scaffold,)).fetchall()

        compounds = []
        activities = []
        for comp, act in rows:
            entry = {"name": comp, "activity": None}
            if act and "pIC50=" in act:
                try:
                    val = float(act.replace("pIC50=", ""))
                    entry["activity"] = val
                    activities.append(val)
                except ValueError:
                    pass
            compounds.append(entry)

        # Deduplicate compounds
        seen = set()
        unique = []
        for c in compounds:
            if c["name"] not in seen:
                seen.add(c["name"])
                unique.append(c)

        avg = sum(activities) / len(activities) if activities else None
        best = max(activities) if activities else None
        worst = min(activities) if activities else None
        spread = (best - worst) if best and worst else None

        profiles.append({
            "scaffold": scaffold,
            "compound_count": len(unique),
            "with_activity": len(activities),
            "avg_pIC50": round(avg, 2) if avg else None,
            "best_pIC50": round(best, 2) if best else None,
            "worst_pIC50": round(worst, 2) if worst else None,
            "spread": round(spread, 2) if spread else None,
            "compounds": unique,
        })

    conn.close()
    profiles.sort(key=lambda x: x["avg_pIC50"] or 0, reverse=True)
    return profiles


@router.get("/sar/heatmap")
def activity_heatmap():
    """Activity data as scaffold x compound matrix for heatmap."""
    conn = sqlite3.connect(settings.db_path)
    rows = conn.execute("""
        SELECT r1.target_value as scaffold, r1.source_entity as compound,
               r2.target_value as activity
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        ORDER BY r1.target_value, r1.source_entity
    """).fetchall()
    conn.close()

    data = []
    for scaffold, compound, activity in rows:
        try:
            val = float(activity.replace("pIC50=", ""))
            data.append({"scaffold": scaffold, "compound": compound, "pIC50": val})
        except ValueError:
            pass
    return data


@router.get("/sar/compare/{scaffold_a}/{scaffold_b}")
def compare_scaffolds(scaffold_a: str, scaffold_b: str):
    """Head-to-head scaffold comparison."""
    from cos.reasoning.comparison import comparison_engine
    return comparison_engine.compare_scaffolds(scaffold_a, scaffold_b)


@router.get("/report/{investigation_id}")
def generate_report(investigation_id: str = "default"):
    """Generate a full investigation report."""
    conn = sqlite3.connect(settings.db_path)
    report = {"investigation_id": investigation_id, "generated_at": "", "sections": []}

    import time
    report["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    # Section 1: Overview
    inv = conn.execute(
        "SELECT title, domain, status, created_at FROM investigations WHERE id=? OR id LIKE ?",
        (investigation_id, investigation_id + "%"),
    ).fetchone()
    if inv:
        report["title"] = inv[0]
        report["domain"] = inv[1]
        report["status"] = inv[2]
    else:
        report["title"] = f"Investigation {investigation_id}"

    # Section 2: Knowledge base counts
    counts = {}
    for table in ["entities", "concepts", "entity_relations", "hypotheses", "decisions"]:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            counts[table] = 0
    report["sections"].append({"title": "Knowledge Base", "data": counts})

    # Section 3: Scaffold SAR
    scaffolds = []
    rows = conn.execute("""
        SELECT r1.target_value, COUNT(DISTINCT r1.source_entity),
               AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)),
               MAX(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL))
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        GROUP BY r1.target_value ORDER BY AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) DESC
    """).fetchall()
    for scaffold, count, avg, best in rows:
        scaffolds.append({"scaffold": scaffold, "compounds": count,
                         "avg_pIC50": round(avg, 2), "best_pIC50": round(best, 2)})
    report["sections"].append({"title": "Scaffold SAR Summary", "data": scaffolds})

    # Section 4: Hypotheses
    hyps = []
    try:
        rows = conn.execute(
            "SELECT statement, confidence, status FROM hypotheses ORDER BY confidence DESC LIMIT 5"
        ).fetchall()
        for stmt, conf, status in rows:
            hyps.append({"statement": stmt, "confidence": conf, "status": status})
    except Exception:
        pass
    report["sections"].append({"title": "Hypotheses", "data": hyps})

    # Section 5: Decisions + risks
    decs = []
    try:
        rows = conn.execute(
            "SELECT title, recommendation, confidence, status FROM decisions ORDER BY confidence DESC LIMIT 3"
        ).fetchall()
        for title, rec, conf, status in rows:
            decs.append({"title": title, "recommendation": rec, "confidence": conf, "status": status})
    except Exception:
        pass
    report["sections"].append({"title": "Decisions", "data": decs})

    # Section 6: AI insights (from learned concepts)
    ai_insights = []
    try:
        rows = conn.execute(
            "SELECT name, definition FROM concepts WHERE domain='ai_analysis' ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        for name, defn in rows:
            ai_insights.append({"topic": name, "insight": defn[:300]})
    except Exception:
        pass
    if ai_insights:
        report["sections"].append({"title": "AI-Generated Insights", "data": ai_insights})

    # Section 7: Risks & gaps
    risks = {}
    try:
        risks["open_conflicts"] = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        risks["low_confidence_concepts"] = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
        risks["risk_assessments"] = conn.execute("SELECT COUNT(*) FROM risk_assessments").fetchone()[0]
    except Exception:
        pass
    report["sections"].append({"title": "Risks & Knowledge Gaps", "data": risks})

    conn.close()
    return report
