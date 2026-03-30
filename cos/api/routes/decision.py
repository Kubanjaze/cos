"""COS API — Decision routes (decisions, actions, risks, tracking)."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class CreateDecisionRequest(BaseModel):
    title: str
    recommendation: str
    confidence: float = 0.5
    investigation_id: str = "default"


@router.post("/decisions")
def create_decision(req: CreateDecisionRequest):
    from cos.decision.schema import decision_store
    did = decision_store.create(req.title, req.recommendation,
                                confidence=req.confidence,
                                investigation_id=req.investigation_id)
    return {"id": did, "title": req.title}


@router.get("/decisions")
def list_decisions(status: Optional[str] = None):
    from cos.decision.schema import decision_store
    decs = decision_store.list_decisions(status=status)
    return [{"id": d.id, "title": d.title, "recommendation": d.recommendation,
             "confidence": d.confidence, "status": d.status,
             "actions": len(d.actions), "risks": len(d.risks)} for d in decs]


@router.get("/decisions/{dec_id}")
def get_decision(dec_id: str):
    from cos.decision.schema import decision_store
    d = decision_store.get(dec_id)
    if not d:
        return {"error": "Not found"}
    return {"id": d.id, "title": d.title, "recommendation": d.recommendation,
            "confidence": d.confidence, "status": d.status,
            "actions": d.actions, "risks": d.risks,
            "invalidation_conditions": d.invalidation_conditions}


@router.post("/decisions/generate-actions")
def generate_actions():
    from cos.decision.actions import action_generator
    return action_generator.generate()


@router.get("/decisions/{dec_id}/risks")
def assess_risks(dec_id: str):
    from cos.decision.risk import risk_assessor
    return risk_assessor.assess(dec_id)


@router.get("/decisions/{dec_id}/tradeoffs")
def analyze_tradeoffs(dec_id: str):
    from cos.decision.tradeoffs import tradeoff_analyzer
    return tradeoff_analyzer.analyze(dec_id)


@router.get("/decisions/{dec_id}/missing")
def missing_evidence(dec_id: str):
    from cos.decision.missing_evidence import missing_evidence_detector
    return missing_evidence_detector.detect(dec_id)


@router.get("/decisions/board/view")
def scenario_board():
    from cos.decision.tracking import decision_tracker
    return decision_tracker.scenario_board()


@router.get("/benchmark/decision")
def decision_benchmark():
    from cos.decision.benchmark import decision_benchmark
    return decision_benchmark.run()
