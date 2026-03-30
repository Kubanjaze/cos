"""COS API — Reasoning routes (synthesis, hypotheses, patterns, insights)."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SynthesizeRequest(BaseModel):
    query: str
    investigation_id: str = "default"


@router.post("/synthesize")
def run_synthesis(req: SynthesizeRequest):
    from cos.reasoning.synthesis import synthesis_engine
    syn = synthesis_engine.synthesize(req.query, investigation_id=req.investigation_id)
    return {"id": syn.id, "query": syn.query, "summary": syn.summary,
            "source_count": syn.source_count, "sources": syn.sources}


@router.get("/hypotheses")
def list_hypotheses(status: Optional[str] = None):
    from cos.reasoning.hypothesis import hypothesis_generator
    return hypothesis_generator.list_hypotheses(status=status)


@router.post("/hypotheses/generate")
def generate_hypotheses():
    from cos.reasoning.hypothesis import hypothesis_generator
    return hypothesis_generator.generate()


@router.get("/hypotheses/{hyp_id}/challenge")
def challenge_hypothesis(hyp_id: str):
    from cos.reasoning.disconfirmation import disconfirmation_engine
    return disconfirmation_engine.challenge(hyp_id)


@router.get("/patterns")
def get_patterns():
    from cos.reasoning.patterns import pattern_detector
    return pattern_detector.detect_all()


@router.get("/insights")
def get_insights():
    from cos.reasoning.insights import insight_extractor
    return insight_extractor.list_insights()


@router.post("/insights/extract")
def extract_insights():
    from cos.reasoning.insights import insight_extractor
    return insight_extractor.extract()


@router.get("/uncertainty")
def system_uncertainty():
    from cos.reasoning.uncertainty import uncertainty_estimator
    return uncertainty_estimator.system_uncertainty()


@router.get("/benchmark/reasoning")
def reasoning_benchmark():
    from cos.reasoning.benchmark import reasoning_benchmark
    return reasoning_benchmark.run_benchmark()


@router.get("/contradictions")
def get_contradictions():
    from cos.reasoning.contradictions import contradiction_analyzer
    return contradiction_analyzer.analyze()
