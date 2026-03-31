"""COS API — Chemistry routes (structures, similarity, activity cliffs)."""

from fastapi import APIRouter
from typing import Optional

router = APIRouter()


@router.get("/chem/compounds")
def get_compounds(scaffold: Optional[str] = None, investigation: Optional[str] = None):
    """All compounds from DB with SVG structures."""
    import sqlite3
    from cos.core.config import settings
    from cos.memory.chemistry import render_svg_base64

    conn = sqlite3.connect(settings.db_path)

    # Get compounds + SMILES + activity + scaffold from DB
    query = """
        SELECT e.name, e.value as smiles, e.investigation_id,
               r_act.target_value as activity,
               r_scaf.target_value as scaffold
        FROM entities e
        LEFT JOIN entity_relations r_act ON e.name = r_act.source_entity AND r_act.relation_type='has_activity'
        LEFT JOIN entity_relations r_scaf ON e.name = r_scaf.source_entity AND r_scaf.relation_type='belongs_to_scaffold'
        WHERE e.entity_type='compound'
    """
    params = []
    if investigation:
        query += " AND e.investigation_id=?"
        params.append(investigation)
    query += " ORDER BY e.name"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    # Load CETP SMILES lookup from CSV (for compounds where DB value is just a name)
    cetp_smiles = {}
    try:
        import csv
        with open("C:/Users/Kerwyn/PycharmProjects/mms-extractor/data/compounds.csv") as f:
            for row in csv.DictReader(f):
                cetp_smiles[row.get("compound_name", "")] = row.get("smiles", "")
    except Exception:
        pass

    compounds = []
    seen = set()
    for name, value, inv_id, activity, scaf in rows:
        if name in seen:
            continue
        seen.add(name)

        # Determine SMILES: use DB value if it looks like SMILES, else look up from CSV
        smiles = ""
        if value and any(c in value for c in ["(", "=", "#", "c1", "C1", "/"]):
            smiles = value
        elif name in cetp_smiles:
            smiles = cetp_smiles[name]

        pic50 = None
        if activity and "pIC50=" in activity:
            try:
                pic50 = float(activity.replace("pIC50=", ""))
            except ValueError:
                pass

        svg = ""
        if smiles and len(smiles) > 5:
            svg = render_svg_base64(smiles, 200, 150)

        entry = {
            "name": name, "smiles": smiles, "pic50": pic50,
            "scaffold": scaf or "unknown", "svg_base64": svg,
            "investigation_id": inv_id,
        }
        if scaffold and entry["scaffold"] != scaffold:
            continue
        compounds.append(entry)

    return compounds


@router.get("/chem/compound/{name}")
def get_compound(name: str):
    """Single compound detail with structure + properties from DB."""
    import sqlite3
    from cos.core.config import settings
    from cos.memory.chemistry import render_svg_base64, chemistry_engine

    conn = sqlite3.connect(settings.db_path)
    row = conn.execute("""
        SELECT e.name, e.value, e.investigation_id,
               r_act.target_value, r_scaf.target_value
        FROM entities e
        LEFT JOIN entity_relations r_act ON e.name=r_act.source_entity AND r_act.relation_type='has_activity'
        LEFT JOIN entity_relations r_scaf ON e.name=r_scaf.source_entity AND r_scaf.relation_type='belongs_to_scaffold'
        WHERE e.entity_type='compound' AND e.name=?
    """, (name,)).fetchone()
    conn.close()

    if not row:
        return {"error": "Compound not found"}

    smiles = row[1] or ""
    pic50 = None
    if row[3] and "pIC50=" in row[3]:
        try:
            pic50 = float(row[3].replace("pIC50=", ""))
        except ValueError:
            pass

    svg = render_svg_base64(smiles, 300, 220) if smiles and "c" in smiles.lower() else ""
    props = chemistry_engine.molecular_properties(smiles) if smiles else {}

    return {"name": row[0], "smiles": smiles, "pic50": pic50,
            "scaffold": row[4] or "unknown", "investigation_id": row[2],
            "svg_base64": svg, "properties": props}


@router.get("/chem/similar/{name}")
def similarity_search(name: str, top_k: int = 10):
    """Find similar compounds by fingerprint — searches ALL compounds in DB."""
    import sqlite3
    from cos.core.config import settings
    from cos.memory.chemistry import render_svg_base64

    conn = sqlite3.connect(settings.db_path)
    # Get query compound SMILES
    query_row = conn.execute("SELECT value FROM entities WHERE name=? AND entity_type='compound'", (name,)).fetchone()
    if not query_row or not query_row[0]:
        conn.close()
        return []

    query_smiles = query_row[0]

    # Get all compounds with SMILES
    rows = conn.execute("""
        SELECT e.name, e.value, e.investigation_id,
               r_act.target_value, r_scaf.target_value
        FROM entities e
        LEFT JOIN entity_relations r_act ON e.name=r_act.source_entity AND r_act.relation_type='has_activity'
        LEFT JOIN entity_relations r_scaf ON e.name=r_scaf.source_entity AND r_scaf.relation_type='belongs_to_scaffold'
        WHERE e.entity_type='compound' AND e.value LIKE '%c%'
    """).fetchall()
    conn.close()

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        query_mol = Chem.MolFromSmiles(query_smiles)
        if not query_mol:
            return []
        query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, 2, nBits=2048)

        results = []
        seen = set()
        for comp_name, smiles, inv_id, activity, scaffold in rows:
            if comp_name in seen:
                continue
            seen.add(comp_name)
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                continue
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            sim = DataStructs.TanimotoSimilarity(query_fp, fp)

            pic50 = None
            if activity and "pIC50=" in activity:
                try:
                    pic50 = float(activity.replace("pIC50=", ""))
                except ValueError:
                    pass

            results.append({
                "name": comp_name, "smiles": smiles, "pic50": pic50,
                "scaffold": scaffold or "unknown", "similarity": round(sim, 4),
                "investigation_id": inv_id,
                "svg_base64": render_svg_base64(smiles, 180, 130),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    except Exception:
        return []


@router.get("/chem/similar-smiles")
def similarity_search_smiles(smiles: str, top_k: int = 10):
    """Find similar compounds by SMILES query."""
    from cos.memory.chemistry import chemistry_engine
    return chemistry_engine.similarity_search(smiles, top_k=top_k)


@router.get("/chem/cliffs")
def activity_cliffs(sim_threshold: float = 0.7, act_threshold: float = 1.0):
    """Detect activity cliffs."""
    from cos.memory.chemistry import chemistry_engine
    return chemistry_engine.detect_activity_cliffs(sim_threshold, act_threshold)


@router.get("/chem/properties/{name}")
def molecular_properties(name: str):
    """Molecular descriptors for a compound."""
    from cos.memory.chemistry import chemistry_engine
    comp = chemistry_engine.get_compound(name)
    if not comp:
        return {"error": "Compound not found"}
    return chemistry_engine.molecular_properties(comp["smiles"])


@router.get("/chem/stats")
def chem_stats():
    from cos.memory.chemistry import chemistry_engine
    return chemistry_engine.stats()
