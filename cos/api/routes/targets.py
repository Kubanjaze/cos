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
    """Discover targets from data: entities typed 'target', investigations, and
    any concept that has compound activity data linked to it."""
    conn = sqlite3.connect(settings.db_path)
    targets = []

    # Source 1: Entities explicitly typed as 'target'
    rows = conn.execute("SELECT DISTINCT name FROM entities WHERE entity_type='target'").fetchall()
    seen = set()
    for (name,) in rows:
        seen.add(name.upper())

    # Source 2: Investigations — match investigation to known target entities/concepts only
    # Don't blindly extract uppercase words — too many false positives (G12C, NSCLC, etc.)
    inv_rows = conn.execute("SELECT id, title FROM investigations").fetchall()
    # We only add targets that already appeared from Source 1 or Source 3
    # Investigations are used later for scoping, not for target discovery

    # Source 3: Concepts that look like biological targets (not methods/metrics/AI)
    rows = conn.execute(
        "SELECT name, definition, domain, confidence FROM concepts "
        "WHERE category NOT IN ('method','metric','recommendation') "
        "AND domain NOT IN ('ai_analysis') "
        "ORDER BY confidence DESC"
    ).fetchall()
    for name, defn, domain, conf in rows:
        if name.upper() not in seen:
            seen.add(name.upper())

    # Source 4: If we have activity data but found nothing, infer a target exists
    if not seen:
        has_activity = conn.execute("SELECT COUNT(*) FROM entity_relations WHERE relation_type='has_activity'").fetchone()[0]
        if has_activity > 0:
            seen.add("UNKNOWN_TARGET")

    # Build target profiles — scope data per target
    # Map targets to investigations by matching target name in title OR investigation ID
    inv_map = {}
    for row in conn.execute("SELECT id, title FROM investigations").fetchall():
        for name in seen:
            if name.lower() in row[1].lower() or name.lower() in row[0].lower():
                inv_map[name] = row[0]

    # Also check: if entities exist with investigation_id containing target name
    for name in seen:
        if name not in inv_map:
            row = conn.execute(
                "SELECT DISTINCT investigation_id FROM entities WHERE investigation_id LIKE ? LIMIT 1",
                (f"%{name.lower()}%",),
            ).fetchone()
            if row:
                inv_map[name] = row[0]

    for name in sorted(seen):
        inv_id = inv_map.get(name)

        # Always scope by investigation if we have one
        if inv_id:
            compounds = conn.execute("SELECT COUNT(DISTINCT name) FROM entities WHERE entity_type='compound' AND investigation_id=?", (inv_id,)).fetchone()[0]
            scaffolds = conn.execute("""
                SELECT COUNT(DISTINCT r.target_value) FROM entity_relations r
                JOIN entities e ON r.source_entity=e.name
                WHERE r.relation_type='belongs_to_scaffold' AND e.investigation_id=?
            """, (inv_id,)).fetchone()[0]
            activities = conn.execute("""
                SELECT COUNT(*) FROM entity_relations r
                JOIN entities e ON r.source_entity=e.name
                WHERE r.relation_type='has_activity' AND e.investigation_id=?
            """, (inv_id,)).fetchone()[0]
        else:
            compounds, scaffolds, activities = 0, 0, 0

        concept = conn.execute(
            "SELECT definition, confidence FROM concepts WHERE UPPER(name)=? ORDER BY confidence DESC LIMIT 1",
            (name,),
        ).fetchone()
        targets.append({
            "name": name, "compounds": compounds, "scaffolds": scaffolds,
            "activities": activities,
            "definition": concept[0] if concept else None,
            "confidence": concept[1] if concept else None,
            "has_data": compounds > 0,
        })

    conn.close()
    return targets


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

    # Find investigation for this target — pick the one with the most compound data
    inv_candidates = conn.execute(
        "SELECT id FROM investigations WHERE LOWER(title) LIKE ? OR LOWER(id) LIKE ?",
        (f"%{target_name.lower()}%", f"%{target_name.lower()}%"),
    ).fetchall()
    # Also check entities
    ent_inv = conn.execute(
        "SELECT DISTINCT investigation_id FROM entities WHERE investigation_id LIKE ?",
        (f"%{target_name.lower()}%",),
    ).fetchall()
    all_inv_ids = list(set([r[0] for r in inv_candidates] + [r[0] for r in ent_inv]))

    # Pick the investigation with the most compounds
    inv_id = None
    best_count = -1
    for iid in all_inv_ids:
        cnt = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type='compound' AND investigation_id=?", (iid,)).fetchone()[0]
        if cnt > best_count:
            best_count = cnt
            inv_id = iid

    # Scaffolds scoped to this target's investigation
    if inv_id:
        scaffolds = conn.execute("""
            SELECT r1.target_value as scaffold, COUNT(DISTINCT r1.source_entity) as compounds,
                   AVG(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as avg_pic50,
                   MAX(CAST(REPLACE(r2.target_value, 'pIC50=', '') AS REAL)) as best
            FROM entity_relations r1
            JOIN entity_relations r2 ON r1.source_entity = r2.source_entity
            JOIN entities e ON r1.source_entity = e.name
            WHERE r1.relation_type='belongs_to_scaffold' AND r2.relation_type='has_activity'
            AND r2.target_value LIKE 'pIC50=%' AND e.investigation_id=?
            GROUP BY scaffold ORDER BY avg_pic50 DESC
        """, (inv_id,)).fetchall()
    else:
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

    # Top compounds scoped to investigation
    if inv_id:
        top_compounds = conn.execute("""
            SELECT r.source_entity, r.target_value
            FROM entity_relations r
            JOIN entities e ON r.source_entity = e.name
            WHERE r.relation_type='has_activity' AND r.target_value LIKE 'pIC50=%' AND e.investigation_id=?
            ORDER BY CAST(REPLACE(r.target_value, 'pIC50=', '') AS REAL) DESC LIMIT 10
        """, (inv_id,)).fetchall()
    else:
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

    # Total counts scoped to investigation
    if inv_id:
        profile["total_compounds"] = conn.execute("SELECT COUNT(DISTINCT name) FROM entities WHERE entity_type='compound' AND investigation_id=?", (inv_id,)).fetchone()[0]
        profile["total_relations"] = conn.execute("""
            SELECT COUNT(*) FROM entity_relations r JOIN entities e ON r.source_entity=e.name WHERE e.investigation_id=?
        """, (inv_id,)).fetchone()[0]
    else:
        profile["total_compounds"] = 0
        profile["total_relations"] = 0

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

        # Auto-assign Murcko scaffolds from SMILES
        scaffold_count = _assign_murcko_scaffolds(conn, investigation_id)

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
        "status": "success", "imported": imported, "skipped": skipped, "scaffolds_assigned": scaffold_count,
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


@router.post("/targets/fetch-chembl")
def fetch_and_ingest_from_chembl(target_name: str = "", investigation_id: str = ""):
    """Fetch real compound data from ChEMBL and ingest into COS."""
    if not target_name:
        return {"status": "error", "message": "target_name required"}

    inv_id = investigation_id or f"inv-{target_name.lower()}"

    # Step 1: Fetch from ChEMBL
    from cos.memory.connectors import connector_registry
    try:
        compounds = connector_registry.fetch("chembl", target_name, investigation_id=inv_id)
    except Exception as e:
        return {"status": "error", "message": f"ChEMBL fetch failed: {e}"}

    if not compounds or (len(compounds) == 1 and "error" in compounds[0]):
        return {"status": "error", "message": compounds[0].get("error", "No data"), "compounds": 0}

    # Step 2: Create investigation if needed
    conn = sqlite3.connect(settings.db_path)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        "INSERT OR IGNORE INTO investigations (id, title, domain, tags, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (inv_id, f"{target_name} inhibitor program", "cheminformatics", target_name.lower(), "active", ts, ts),
    )

    # Step 3: Add target concept
    concept_id = f"con-{uuid.uuid4().hex[:8]}"
    target_info = compounds[0].get("target", target_name)
    conn.execute(
        "INSERT OR IGNORE INTO concepts (id, name, name_lower, definition, domain, category, confidence, source_ref, investigation_id, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (concept_id, target_name.upper(), target_name.lower(),
         f"{target_info} — target with {len(compounds)} compounds in ChEMBL",
         "cheminformatics", "target", 0.9, "chembl", inv_id, ts, ts),
    )

    # Step 4: Ingest compounds
    ingested = 0
    for comp in compounds:
        name = comp.get("compound_name", comp.get("chembl_id", ""))
        smiles = comp.get("smiles", "")
        pic50 = comp.get("pic50")
        if not name or pic50 is None:
            continue

        # Entity
        eid = f"ent-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT OR IGNORE INTO entities (id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (eid, "compound", name, smiles or name, None, f"chembl-{target_name.lower()}", inv_id, 1.0, ts),
        )

        # Activity relation
        rid = f"rel-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT OR IGNORE INTO entity_relations (id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (rid, name, "has_activity", f"pIC50={pic50}", 1.0, None, f"chembl-{target_name.lower()}", ts),
        )

        # Target entity
        tid = f"ent-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT OR IGNORE INTO entities (id, entity_type, name, value, source_chunk_id, document_id, investigation_id, confidence, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (tid, "target", target_name.upper(), target_name.upper(), None, f"chembl-{target_name.lower()}", inv_id, 1.0, ts),
        )

        ingested += 1

    # Step 5: Assign Murcko scaffold families from structures
    scaffold_count = _assign_murcko_scaffolds(conn, inv_id)

    conn.commit()
    conn.close()

    return {"status": "success", "target": target_name, "investigation_id": inv_id,
            "fetched": len(compounds), "ingested": ingested, "scaffolds_assigned": scaffold_count}


def _assign_murcko_scaffolds(conn, investigation_id: str) -> int:
    """Compute Murcko scaffolds from SMILES and create belongs_to_scaffold relations."""
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
    except ImportError:
        return 0

    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    # Get compounds with SMILES that don't have scaffold relations yet
    rows = conn.execute("""
        SELECT e.name, e.value FROM entities e
        LEFT JOIN entity_relations r ON e.name = r.source_entity AND r.relation_type='belongs_to_scaffold'
        WHERE e.entity_type='compound' AND e.investigation_id=? AND r.id IS NULL
        AND e.value LIKE '%c%'
    """, (investigation_id,)).fetchall()

    # Group by Murcko scaffold
    scaffold_map = {}
    for name, smiles in rows:
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                continue
            core = MurckoScaffold.GetScaffoldForMol(mol)
            generic = MurckoScaffold.MakeScaffoldGeneric(core)
            scaffold_smiles = Chem.MolToSmiles(generic)
            scaffold_map.setdefault(scaffold_smiles, []).append(name)
        except Exception:
            continue

    # Name scaffolds by frequency (Scaffold_A, Scaffold_B, ...)
    sorted_scaffolds = sorted(scaffold_map.items(), key=lambda x: -len(x[1]))
    assigned = 0

    for i, (smi, compounds) in enumerate(sorted_scaffolds):
        scaffold_name = f"Scaffold_{chr(65 + i)}" if i < 26 else f"Scaffold_{i+1}"

        for compound_name in compounds:
            rel_id = f"rel-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT OR IGNORE INTO entity_relations (id, source_entity, relation_type, target_value, confidence, source_chunk_id, document_id, created_at) "
                "VALUES (?, ?, 'belongs_to_scaffold', ?, 1.0, NULL, ?, ?)",
                (rel_id, compound_name, scaffold_name, f"chembl-{investigation_id}", ts),
            )
            assigned += 1

    return assigned


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
