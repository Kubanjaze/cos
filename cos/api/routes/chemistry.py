"""COS API — Chemistry routes (structures, similarity, activity cliffs)."""

from fastapi import APIRouter
from typing import Optional

router = APIRouter()


@router.get("/chem/compounds")
def get_compounds(scaffold: Optional[str] = None):
    """All compounds with SVG structures."""
    from cos.memory.chemistry import chemistry_engine
    compounds = chemistry_engine.get_compounds_with_structures()
    if scaffold:
        compounds = [c for c in compounds if c["scaffold"] == scaffold]
    return compounds


@router.get("/chem/compound/{name}")
def get_compound(name: str):
    """Single compound detail with structure + properties."""
    from cos.memory.chemistry import chemistry_engine
    comp = chemistry_engine.get_compound(name)
    if not comp:
        return {"error": "Compound not found"}
    props = chemistry_engine.molecular_properties(comp["smiles"])
    return {**comp, "properties": props}


@router.get("/chem/similar/{name}")
def similarity_search(name: str, top_k: int = 10):
    """Find similar compounds by fingerprint."""
    from cos.memory.chemistry import chemistry_engine
    return chemistry_engine.search_by_name(name, top_k=top_k)


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
