from __future__ import annotations

from typing import TypedDict

from agent.schemas import AgentReport, AnalysisContext, RouteDecision


class WorkflowState(TypedDict, total=False):
    question: str
    manual_type: str | None
    route_decision: RouteDecision
    context: AnalysisContext
    report: AgentReport
