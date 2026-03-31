"""COS chemistry module — RDKit-powered structure rendering, similarity, activity cliffs.

Sprint 1: "Make it visual" — molecular structures, fingerprint search, cliff detection.
"""

import csv
import io
import base64
import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.memory.chemistry")

COMPOUNDS_CSV = "C:/Users/Kerwyn/PycharmProjects/mms-extractor/data/compounds.csv"


def _load_compounds() -> list[dict]:
    """Load compound data from CSV."""
    compounds = []
    try:
        with open(COMPOUNDS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                compounds.append({
                    "name": row.get("compound_name", ""),
                    "smiles": row.get("smiles", ""),
                    "pic50": float(row["pic50"]) if row.get("pic50") else None,
                })
    except Exception as e:
        logger.warning(f"Failed to load compounds: {e}")
    return compounds


def render_svg(smiles: str, width: int = 250, height: int = 180) -> str:
    """Render SMILES to SVG string."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return ""
        drawer = Draw.MolDraw2DSVG(width, height)
        drawer.drawOptions().addStereoAnnotation = True
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()
    except Exception:
        return ""


def render_svg_base64(smiles: str, width: int = 250, height: int = 180) -> str:
    """Render SMILES to base64-encoded SVG for embedding in HTML."""
    svg = render_svg(smiles, width, height)
    if not svg:
        return ""
    return base64.b64encode(svg.encode()).decode()


class ChemistryEngine:
    """RDKit-powered chemistry operations."""

    def __init__(self):
        self._compounds = None
        self._fps = None

    def _ensure_loaded(self):
        if self._compounds is None:
            self._compounds = _load_compounds()

    def get_compounds_with_structures(self) -> list[dict]:
        """Return all compounds with SVG structures."""
        self._ensure_loaded()
        results = []
        for c in self._compounds:
            svg = render_svg_base64(c["smiles"], 200, 150)
            scaffold = c["name"].split("_")[0] if "_" in c["name"] else "other"
            results.append({
                "name": c["name"], "smiles": c["smiles"], "pic50": c["pic50"],
                "scaffold": scaffold, "svg_base64": svg,
            })
        return results

    def get_compound(self, name: str) -> Optional[dict]:
        """Get a single compound with structure."""
        self._ensure_loaded()
        for c in self._compounds:
            if c["name"].lower() == name.lower():
                svg = render_svg_base64(c["smiles"], 300, 220)
                scaffold = c["name"].split("_")[0] if "_" in c["name"] else "other"
                return {"name": c["name"], "smiles": c["smiles"], "pic50": c["pic50"],
                        "scaffold": scaffold, "svg_base64": svg}
        return None

    def similarity_search(self, query_smiles: str, top_k: int = 10) -> list[dict]:
        """Find most similar compounds by Tanimoto fingerprint similarity."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, DataStructs

            query_mol = Chem.MolFromSmiles(query_smiles)
            if not query_mol:
                return []
            query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, 2, nBits=2048)

            self._ensure_loaded()
            results = []
            for c in self._compounds:
                mol = Chem.MolFromSmiles(c["smiles"])
                if not mol:
                    continue
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                sim = DataStructs.TanimotoSimilarity(query_fp, fp)
                results.append({
                    "name": c["name"], "smiles": c["smiles"], "pic50": c["pic50"],
                    "scaffold": c["name"].split("_")[0],
                    "similarity": round(sim, 4),
                    "svg_base64": render_svg_base64(c["smiles"], 180, 130),
                })

            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def search_by_name(self, query_name: str, top_k: int = 10) -> list[dict]:
        """Similarity search using a compound name instead of SMILES."""
        self._ensure_loaded()
        for c in self._compounds:
            if c["name"].lower() == query_name.lower():
                return self.similarity_search(c["smiles"], top_k=top_k)
        return []

    def detect_activity_cliffs(self, similarity_threshold: float = 0.7,
                                activity_threshold: float = 1.0) -> list[dict]:
        """Find compound pairs with high similarity but large activity difference."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, DataStructs

            self._ensure_loaded()
            active = [c for c in self._compounds if c["pic50"] is not None]

            # Compute fingerprints
            fps = []
            for c in active:
                mol = Chem.MolFromSmiles(c["smiles"])
                if mol:
                    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                    fps.append((c, fp))

            cliffs = []
            for i in range(len(fps)):
                for j in range(i + 1, len(fps)):
                    c1, fp1 = fps[i]
                    c2, fp2 = fps[j]
                    sim = DataStructs.TanimotoSimilarity(fp1, fp2)
                    if sim >= similarity_threshold:
                        delta = abs(c1["pic50"] - c2["pic50"])
                        if delta >= activity_threshold:
                            more_active = c1 if c1["pic50"] > c2["pic50"] else c2
                            less_active = c2 if c1["pic50"] > c2["pic50"] else c1
                            cliffs.append({
                                "compound_a": more_active["name"],
                                "smiles_a": more_active["smiles"],
                                "pic50_a": more_active["pic50"],
                                "compound_b": less_active["name"],
                                "smiles_b": less_active["smiles"],
                                "pic50_b": less_active["pic50"],
                                "similarity": round(sim, 4),
                                "activity_delta": round(delta, 2),
                                "scaffold_a": more_active["name"].split("_")[0],
                                "scaffold_b": less_active["name"].split("_")[0],
                                "svg_a": render_svg_base64(more_active["smiles"], 180, 130),
                                "svg_b": render_svg_base64(less_active["smiles"], 180, 130),
                            })

            cliffs.sort(key=lambda x: x["activity_delta"], reverse=True)
            logger.info(f"Activity cliffs: {len(cliffs)} found (sim>={similarity_threshold}, delta>={activity_threshold})")
            return cliffs
        except Exception as e:
            logger.error(f"Activity cliff detection failed: {e}")
            return []

    def molecular_properties(self, smiles: str) -> dict:
        """Compute molecular descriptors."""
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {}
            return {
                "molecular_weight": round(Descriptors.MolWt(mol), 2),
                "logp": round(Descriptors.MolLogP(mol), 2),
                "hbd": Descriptors.NumHDonors(mol),
                "hba": Descriptors.NumHAcceptors(mol),
                "tpsa": round(Descriptors.TPSA(mol), 2),
                "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
                "rings": Descriptors.RingCount(mol),
                "heavy_atoms": Descriptors.HeavyAtomCount(mol),
            }
        except Exception:
            return {}

    def stats(self) -> dict:
        self._ensure_loaded()
        active = sum(1 for c in self._compounds if c["pic50"] is not None)
        return {"total_compounds": len(self._compounds), "with_activity": active}


chemistry_engine = ChemistryEngine()
