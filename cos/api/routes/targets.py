"""COS API — Target profile + assay import + compound recommender."""

import csv
import io
import sqlite3
import time
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from cos.core.config import settings

router = APIRouter()


@router.get("/targets")
def list_targets():
    """List all known targets — from entities + concepts + known target names."""
    conn = sqlite3.connect(settings.db_path)
    target_names = set()

    # From target entities
    rows = conn.execute("SELECT DISTINCT name FROM entities WHERE entity_type='target'").fetchall()
    for (name,) in rows:
        target_names.add(name)

    # From concepts explicitly categorized as targets
    rows = conn.execute(
        "SELECT DISTINCT name FROM concepts WHERE category='target'"
    ).fetchall()
    for (name,) in rows:
        target_names.add(name)

    # Fallback: if still empty, add CETP as default (we know it's the project target)
    if not target_names:
        target_names.add("CETP")

    compound_count = conn.execute(
        "SELECT COUNT(DISTINCT name) FROM entities WHERE entity_type='compound'"
    ).fetchone()[0]

    result = []
    for name in sorted(target_names):
        concept = conn.execute(
            "SELECT definition, confidence FROM concepts WHERE name_lower=? ORDER BY confidence DESC LIMIT 1",
            (name.lower(),),
        ).fetchone()
        result.append({
            "name": name, "compounds": compound_count,
            "definition": concept[0] if concept else None,
            "confidence": concept[1] if concept else None,
        })

    conn.close()
    return result


@router.get("/targets/{target_name}")
def target_profile(target_name: str):
    """Full profile for a target: definition, compounds, SAR, hypotheses."""
    conn = sqlite3.connect(settings.db_path)

    # Basic info
    concept = conn.execute(
        "SELECT name, definition, domain, confidence FROM concepts WHERE name_lower=?",
        (target_name.lower(),),
    ).fetchone()

    profile = {
        "target": target_name,
        "definition": concept[1] if concept else f"Target: {target_name}",
        "domain": concept[2] if concept else "unknown",
        "confidence": concept[3] if concept else None,
    }

    # All scaffolds with activity data
    scaffolds = conn.execute("""
        SELECT r1.target_value as scaffold, COUNT(DISTINCT r1.source_entity) as compounds,
               AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg_pic50,
               MAX(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as best
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        GROUP BY scaffold ORDER BY avg_pic50 DESC
    """).fetchall()
    profile["scaffolds"] = [
        {"name": s[0], "compounds": s[1], "avg_pIC50": round(s[2], 2), "best_pIC50": round(s[3], 2)}
        for s in scaffolds
    ]

    # Top compounds
    top_compounds = conn.execute("""
        SELECT r.source_entity, r.target_value
        FROM entity_relations r WHERE r.relation_type='has_activity'
        AND r.target_value LIKE 'pIC50=%'
        ORDER BY CAST(REPLACE(r.target_value, 'pIC50=', '') AS REAL) DESC LIMIT 10
    """).fetchall()
    profile["top_compounds"] = [
        {"name": c[0], "activity": c[1]} for c in top_compounds
    ]

    # Hypotheses related to this target
    try:
        hyps = conn.execute(
            "SELECT id, statement, confidence, status FROM hypotheses ORDER BY confidence DESC LIMIT 5"
        ).fetchall()
        profile["hypotheses"] = [
            {"id": h[0], "statement": h[1], "confidence": h[2], "status": h[3]} for h in hyps
        ]
    except Exception:
        profile["hypotheses"] = []

    # Decisions
    try:
        decs = conn.execute(
            "SELECT id, title, confidence, status FROM decisions ORDER BY confidence DESC LIMIT 3"
        ).fetchall()
        profile["decisions"] = [
            {"id": d[0], "title": d[1], "confidence": d[2], "status": d[3]} for d in decs
        ]
    except Exception:
        profile["decisions"] = []

    # Total counts
    profile["total_compounds"] = conn.execute("SELECT COUNT(DISTINCT name) FROM entities WHERE entity_type='compound'").fetchone()[0]
    profile["total_relations"] = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]

    conn.close()
    return profile


@router.post("/assay/preview")
async def preview_assay_data(file: UploadFile = File(...)):
    """Preview CSV file: return columns, row count, and first 10 rows for mapping."""
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    rows = []
    for i, row in enumerate(reader):
        if i >= 100:
            break
        rows.append(dict(row))
    return {"columns": columns, "row_count": len(rows), "preview": rows[:10], "all_rows": rows}


@router.post("/assay/import")
async def import_assay_data(file: UploadFile = File(...), investigation_id: str = Form("default"),
                             compound_col: str = Form("compound_name"),
                             activity_col: str = Form("activity_value"),
                             activity_type_col: str = Form(""),
                             smiles_col: str = Form("")):
    """Import assay data with column mapping. Creates backup before import."""
    import shutil, os

    # Step 1: Backup database
    db_path = settings.db_path
    backup_path = db_path + f".backup.{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(db_path, backup_path)
        backup_size = os.path.getsize(backup_path)
    except Exception as e:
        return {"status": "error", "message": f"Backup failed: {e}"}

    # Step 2: Parse CSV
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    conn = sqlite3.connect(db_path)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    imported = 0
    skipped = 0
    errors = []

    try:
        for row_num, row in enumerate(reader, 1):
            compound = row.get(compound_col, "").strip()
            act_value = row.get(activity_col, "").strip()
            if not compound or not act_value:
                skipped += 1
                continue

            act_type = row.get(activity_type_col, "pIC50").strip() if activity_type_col else "pIC50"
            smiles = row.get(smiles_col, "").strip() if smiles_col else ""

            try:
                # Insert entity
                ent_id = f"ent-{uuid.uuid4().hex[:8]}"
                conn.execute(
                    "INSERT OR IGNORE INTO entities (id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at) "
                    "VALUES (?, 'compound', ?, ?, NULL, 'assay-import', ?, 1.0, ?)",
                    (ent_id, compound, smiles or compound, investigation_id, ts),
                )

                # Insert activity
                rel_id = f"rel-{uuid.uuid4().hex[:8]}"
                conn.execute(
                    "INSERT OR IGNORE INTO entity_relations (id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at) "
                    "VALUES (?, ?, 'has_activity', ?, 1.0, NULL, 'assay-import', ?)",
                    (rel_id, compound, f"{act_type}={act_value}", ts),
                )

                # Scaffold from name prefix
                prefix = compound.split("_")[0] if "_" in compound else None
                if prefix:
                    scaf_id = f"rel-{uuid.uuid4().hex[:8]}"
                    conn.execute(
                        "INSERT OR IGNORE INTO entity_relations (id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at) "
                        "VALUES (?, ?, 'belongs_to_scaffold', ?, 1.0, NULL, 'assay-import', ?)",
                        (scaf_id, compound, prefix, ts),
                    )

                imported += 1
            except Exception as e:
                errors.append({"row": row_num, "compound": compound, "error": str(e)[:80]})
                if len(errors) > 20:
                    break

        conn.commit()
    except Exception as e:
        conn.close()
        # Restore backup on failure
        try:
            shutil.copy2(backup_path, db_path)
        except Exception:
            pass
        return {"status": "error", "message": f"Import failed (backup restored): {e}",
                "backup_path": backup_path}

    conn.close()
    return {
        "status": "success", "imported": imported, "skipped": skipped,
        "errors": errors[:10], "filename": file.filename,
        "backup_path": backup_path, "backup_size": backup_size,
        "column_mapping": {"compound": compound_col, "activity": activity_col,
                           "activity_type": activity_type_col, "smiles": smiles_col},
    }


@router.post("/assay/rollback")
def rollback_import(backup_path: str = ""):
    """Restore database from backup."""
    import shutil, os, glob
    db_path = settings.db_path

    if not backup_path:
        # Find most recent backup
        backups = sorted(glob.glob(db_path + ".backup.*"), reverse=True)
        if not backups:
            return {"status": "error", "message": "No backups found"}
        backup_path = backups[0]

    if not os.path.exists(backup_path):
        return {"status": "error", "message": f"Backup not found: {backup_path}"}

    try:
        shutil.copy2(backup_path, db_path)
        return {"status": "success", "restored_from": backup_path,
                "size": os.path.getsize(db_path)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/assay/backups")
def list_backups():
    """List available database backups."""
    import os, glob
    db_path = settings.db_path
    backups = sorted(glob.glob(db_path + ".backup.*"), reverse=True)
    return [{"path": b, "size": os.path.getsize(b),
             "created": b.split(".backup.")[-1]} for b in backups]


@router.get("/recommend/next")
def recommend_next_compound():
    """Recommend what compound to make next based on SAR gaps."""
    conn = sqlite3.connect(settings.db_path)

    recommendations = []

    # Strategy 1: Best scaffold, explore more substituents
    best_scaffold = conn.execute("""
        SELECT r1.target_value, AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg,
               COUNT(DISTINCT r1.source_entity) as cnt
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        GROUP BY r1.target_value ORDER BY avg DESC LIMIT 1
    """).fetchone()

    if best_scaffold:
        recommendations.append({
            "strategy": "expand_best_scaffold",
            "scaffold": best_scaffold[0],
            "rationale": f"'{best_scaffold[0]}' has the highest avg pIC50 ({best_scaffold[2]:.2f}) with {best_scaffold[2]} compounds. "
                        f"Synthesize more analogs with diverse substituents to map SAR.",
            "priority": 0.9,
            "effort": "medium",
        })

    # Strategy 2: Investigate activity cliffs
    from cos.memory.chemistry import chemistry_engine
    cliffs = chemistry_engine.detect_activity_cliffs(0.5, 1.0)
    if cliffs:
        top_cliff = cliffs[0]
        recommendations.append({
            "strategy": "investigate_cliff",
            "compounds": [top_cliff["compound_a"], top_cliff["compound_b"]],
            "rationale": f"Activity cliff: {top_cliff['compound_a']} (pIC50={top_cliff['pic50_a']}) vs "
                        f"{top_cliff['compound_b']} (pIC50={top_cliff['pic50_b']}), "
                        f"similarity={top_cliff['similarity']:.0%}. Design analogs that merge favorable features.",
            "priority": 0.85,
            "effort": "low",
        })

    # Strategy 3: Fill scaffold gaps (least-explored active scaffold)
    least_explored = conn.execute("""
        SELECT r1.target_value, COUNT(DISTINCT r1.source_entity) as cnt,
               AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        GROUP BY r1.target_value HAVING avg > 6.5 ORDER BY cnt ASC LIMIT 1
    """).fetchone()

    if least_explored:
        recommendations.append({
            "strategy": "explore_undersampled",
            "scaffold": least_explored[0],
            "rationale": f"'{least_explored[0]}' shows promising activity (avg pIC50={least_explored[2]:.2f}) but only "
                        f"{least_explored[1]} compounds tested. Expand to confirm SAR trends.",
            "priority": 0.75,
            "effort": "medium",
        })

    # Strategy 4: Cross-scaffold hybrid
    top2 = conn.execute("""
        SELECT r1.target_value, AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg
        FROM entity_relations r1
        JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
        WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
        AND r2.target_value LIKE 'pIC50=%'
        GROUP BY r1.target_value ORDER BY avg DESC LIMIT 2
    """).fetchall()

    if len(top2) == 2:
        recommendations.append({
            "strategy": "scaffold_hybrid",
            "scaffolds": [top2[0][0], top2[1][0]],
            "rationale": f"Design hybrid molecules combining features of '{top2[0][0]}' (avg {top2[0][1]:.2f}) "
                        f"and '{top2[1][0]}' (avg {top2[1][1]:.2f}) scaffolds.",
            "priority": 0.6,
            "effort": "high",
        })

    conn.close()
    recommendations.sort(key=lambda x: x["priority"], reverse=True)
    return recommendations
