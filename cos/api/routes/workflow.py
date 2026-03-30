"""COS API — Workflow routes (definitions, runs, templates, schedules)."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/workflows")
def list_workflows():
    from cos.workflow.schema import workflow_schema
    return workflow_schema.list_workflows()


@router.get("/workflows/templates")
def list_templates():
    from cos.workflow.templates import template_registry
    return template_registry.list_templates()


class RunWorkflowRequest(BaseModel):
    workflow_name: str
    investigation_id: str = "default"


@router.post("/workflows/run")
def run_workflow(req: RunWorkflowRequest):
    from cos.workflow.executor import workflow_executor
    return workflow_executor.execute(req.workflow_name, investigation_id=req.investigation_id)


@router.get("/workflows/runs")
def list_runs():
    from cos.workflow.executor import workflow_executor
    return workflow_executor.list_runs()


@router.get("/workflows/analytics")
def workflow_analytics():
    from cos.workflow.analytics import workflow_analytics
    return workflow_analytics.performance_report()


@router.get("/workflows/stats")
def workflow_stats():
    from cos.workflow.executor import workflow_executor
    return workflow_executor.stats()
