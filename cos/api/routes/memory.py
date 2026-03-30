"""COS API — Memory routes (entities, concepts, graph, search, gaps)."""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/entities")
def list_entities(entity_type: Optional[str] = None):
    from cos.memory.entities import entity_extractor
    ents = entity_extractor.get_entities(entity_type=entity_type)
    return [{"id": e.id, "name": e.name, "type": e.entity_type,
             "confidence": e.confidence, "document_id": e.document_id} for e in ents]


@router.get("/concepts")
def list_concepts(domain: Optional[str] = None):
    from cos.memory.semantic import semantic_memory
    concepts = semantic_memory.list_concepts(domain=domain)
    return [{"id": c.id, "name": c.name, "definition": c.definition,
             "domain": c.domain, "category": c.category, "confidence": c.confidence} for c in concepts]


@router.get("/graph/{entity_name}")
def get_graph(entity_name: str, depth: int = 1):
    from cos.memory.graph import knowledge_graph
    return knowledge_graph.subgraph(entity_name, depth=depth)


@router.get("/graph/neighbors/{entity_name}")
def get_neighbors(entity_name: str):
    from cos.memory.graph import knowledge_graph
    return knowledge_graph.neighbors(entity_name)


@router.get("/graph/stats")
def graph_stats():
    from cos.memory.graph import knowledge_graph
    return knowledge_graph.stats()


@router.get("/search")
def hybrid_search(q: str, top_k: int = 10):
    from cos.memory.hybrid_query import hybrid_engine
    return hybrid_engine.search(q, top_k=top_k)


@router.get("/chat")
def chat_query(q: str):
    from cos.interface.chat import chat_interface
    return chat_interface.query(q)


@router.get("/gaps")
def get_gaps():
    from cos.memory.gaps import gap_detector
    return gap_detector.summary()


@router.get("/domains")
def get_domains():
    from cos.memory.visualization import memory_viz
    return memory_viz.domain_clusters()


@router.get("/provenance/{target_type}/{target_id}")
def get_provenance(target_type: str, target_id: str):
    from cos.memory.provenance import provenance_tracker
    links = provenance_tracker.trace(target_type, target_id)
    return [{"source_type": l.source_type, "source_id": l.source_id,
             "operation": l.operation, "agent": l.agent} for l in links]


@router.get("/memory/scores")
def get_scores(target_type: Optional[str] = None, limit: int = 20):
    from cos.memory.scoring import memory_scorer
    top = memory_scorer.get_top(target_type=target_type, limit=limit)
    return [{"type": s.target_type, "id": s.target_id, "composite": s.composite_score,
             "relevance": s.relevance, "confidence": s.confidence, "frequency": s.frequency} for s in top]


@router.get("/chat/suggestions")
def chat_suggestions():
    from cos.interface.chat import chat_interface
    return chat_interface.get_suggested_queries()


@router.get("/llm/ask")
def llm_ask(q: str):
    from cos.interface.llm_chat import llm_chat
    return llm_chat.ask(q)


@router.get("/llm/spend")
def llm_spend():
    from cos.interface.llm_chat import llm_chat
    return llm_chat.get_spend_summary()
