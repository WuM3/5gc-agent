from pathlib import Path

from agent.pipeline import AgentPipeline
from agent.schemas import LLMResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeOfflineLLM:
    def generate(self, prompt: str) -> LLMResult:
        return LLMResult(content="", mode="offline", error="fake offline")


def test_pipeline_uses_graph_workflow_backend():
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=FakeOfflineLLM())

    assert pipeline.workflow.backend_name in {"langgraph", "sequential"}


def test_graph_workflow_runs_route_analyze_and_report():
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("UE 注册成功但不能上网，应该怎么排查？", manual_type="知识查询")

    assert report.mode == "offline"
    assert report.context.question_type.value == "故障分析"
    assert report.context.selected_question_type.value == "知识查询"
    assert report.context.detected_question_type.value == "故障分析"
    assert report.context.route_warning
    assert report.context.case_hits
    assert "建议排查步骤" in report.content
