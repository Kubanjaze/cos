"""COS API — Autonomy routes (auto investigate, monitor, agents, simulation)."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class InvestigateRequest(BaseModel):
    question: str
    investigation_id: str = "default"


@router.post("/auto/investigate")
def autonomous_investigate(req: InvestigateRequest):
    from cos.autonomy.autonomous import autonomous_investigation
    return autonomous_investigation.run(req.question, investigation_id=req.investigation_id)


@router.get("/auto/monitor")
def system_monitor():
    from cos.autonomy.autonomous import continuous_monitor
    return continuous_monitor.check()


@router.get("/auto/priorities")
def get_priorities():
    from cos.autonomy.autonomous import priority_scheduler
    return priority_scheduler.schedule_by_priority()


@router.get("/auto/optimize")
def cost_optimization():
    from cos.autonomy.autonomous import cost_optimizer_ai
    return cost_optimizer_ai.optimize()


class ConsultRequest(BaseModel):
    query: str


@router.post("/intel/consult")
def agent_consult(req: ConsultRequest):
    from cos.intelligence.agents import multi_agent_system
    return multi_agent_system.consult(req.query)


@router.post("/intel/debate")
def agent_debate(req: ConsultRequest):
    from cos.intelligence.agents import multi_agent_system
    return multi_agent_system.debate(req.query)


@router.get("/intel/agents")
def list_agents():
    from cos.intelligence.agents import multi_agent_system
    return multi_agent_system.list_agents()


@router.get("/benchmark/intelligence")
def intelligence_benchmark():
    from cos.intelligence.meta import intelligence_benchmark
    return intelligence_benchmark.run()


@router.get("/intel/meta")
def meta_reasoning():
    from cos.intelligence.meta import meta_reasoner
    return meta_reasoner.assess_reasoning_quality()
