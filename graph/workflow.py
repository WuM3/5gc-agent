from __future__ import annotations

from agent.router import resolve_question_type
from graph.state import WorkflowState


class AgentWorkflow:
    def __init__(self, analyzer, report_generator):
        self.analyzer = analyzer
        self.report_generator = report_generator
        self.backend_name = "sequential"
        self._compiled = self._build_langgraph()

    def invoke(self, state: WorkflowState) -> WorkflowState:
        if self._compiled is not None:
            return self._compiled.invoke(state)
        return self._run_sequential(state)

    def _build_langgraph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            return None

        workflow = StateGraph(WorkflowState)
        workflow.add_node("route", self._route_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("report", self._report_node)
        workflow.add_edge(START, "route")
        workflow.add_edge("route", "analyze")
        workflow.add_edge("analyze", "report")
        workflow.add_edge("report", END)
        self.backend_name = "langgraph"
        return workflow.compile()

    def _run_sequential(self, state: WorkflowState) -> WorkflowState:
        state = {**state, **self._route_node(state)}
        state = {**state, **self._analyze_node(state)}
        state = {**state, **self._report_node(state)}
        return state

    def _route_node(self, state: WorkflowState) -> WorkflowState:
        return {
            "route_decision": resolve_question_type(
                state["question"],
                manual_type=state.get("manual_type"),
            )
        }

    def _analyze_node(self, state: WorkflowState) -> WorkflowState:
        route_decision = state["route_decision"]
        return {
            "context": self.analyzer.analyze(
                state["question"],
                route_decision.final_type,
                route_decision=route_decision,
            )
        }

    def _report_node(self, state: WorkflowState) -> WorkflowState:
        return {"report": self.report_generator.generate(state["context"])}
