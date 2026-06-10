from pathlib import Path

from agent.schemas import LLMResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeOnlineLLM:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> LLMResult:
        self.prompts.append(prompt)
        return LLMResult(content="在线结构化报告", mode="online")


class FakeOfflineLLM:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> LLMResult:
        self.prompts.append(prompt)
        return LLMResult(content="", mode="offline", error="fake offline")


def test_online_pipeline_uses_evidence_prompt_and_llm_content():
    from agent.pipeline import AgentPipeline

    llm = FakeOnlineLLM()
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=llm)

    report = pipeline.run("SMF 日志中出现 DNN not supported")

    assert report.mode == "online"
    assert report.content == "在线结构化报告"
    assert report.context.knowledge_hits
    assert report.context.case_hits
    assert report.context.rule_hits
    assert llm.prompts
    assert "命中的知识片段" in llm.prompts[0]
    assert "命中的故障案例" in llm.prompts[0]
    assert "命中的日志规则" in llm.prompts[0]


def test_offline_pipeline_builds_structured_report_from_context():
    from agent.pipeline import AgentPipeline

    llm = FakeOfflineLLM()
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=llm)

    report = pipeline.run("UE 注册成功但不能上网")

    assert len(llm.prompts) == 1
    assert "命中的知识片段" in llm.prompts[0]
    assert "命中的故障案例" in llm.prompts[0]
    assert "命中的日志规则" in llm.prompts[0]
    assert report.mode == "offline"
    assert "问题类型：" in report.content
    assert "涉及网元：" in report.content
    assert "建议排查步骤：" in report.content
    assert report.context.case_hits


def test_evidence_formatters_accept_pipeline_report_context():
    from agent.pipeline import AgentPipeline
    from agent.report import format_case_hits, format_knowledge_hits, format_rule_hits

    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("SMF 日志中出现 DNN not supported")

    assert "DNN" in format_knowledge_hits(report.context)
    assert "FC-005" in format_case_hits(report.context)
    assert "DNN not supported" in format_rule_hits(report.context)


def test_offline_knowledge_question_includes_matched_knowledge_snippet():
    from agent.pipeline import AgentPipeline

    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("什么是核心网")

    assert report.mode == "offline"
    assert "5G 核心网" in report.content
    assert "控制面" in report.content
    assert "用户面" in report.content


def test_manual_type_override_is_kept_in_pipeline_context():
    from agent.pipeline import AgentPipeline

    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("AMF 的作用是什么？", manual_type="故障诊断")

    assert report.context.question_type.value == "故障诊断"


def test_manual_knowledge_query_searches_only_knowledge_sources():
    from agent.pipeline import AgentPipeline

    llm = FakeOnlineLLM()
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=llm)

    report = pipeline.run("SMF 日志中出现 DNN not supported", manual_type="知识查询")

    assert report.context.question_type.value == "知识查询"
    assert report.context.knowledge_hits
    assert report.context.case_hits == []
    assert report.context.rule_hits == []
    assert "知识回答" in llm.prompts[0]


def test_manual_procedure_query_prefers_procedure_knowledge():
    from agent.pipeline import AgentPipeline

    llm = FakeOnlineLLM()
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=llm)

    report = pipeline.run("PDU Session 建立流程经过哪些网元？", manual_type="流程解释")

    assert report.context.question_type.value == "流程解释"
    assert report.context.knowledge_hits
    assert report.context.knowledge_hits[0].source == "procedures.md"
    assert report.context.case_hits == []
    assert report.context.rule_hits == []
    assert "流程说明" in llm.prompts[0]


def test_manual_log_analysis_prioritizes_log_rules_before_fault_cases():
    from agent.pipeline import AgentPipeline

    llm = FakeOnlineLLM()
    pipeline = AgentPipeline(root_dir=PROJECT_ROOT, llm_client=llm)

    report = pipeline.run("registered but cannot ping internet", manual_type="日志分析")

    assert report.context.question_type.value == "日志分析"
    assert report.context.rule_hits
    assert report.context.case_hits
    assert report.context.rule_hits[0].nf == "UPF"
    assert report.context.network_functions[0] == "UPF"
    assert "日志分析结果" in llm.prompts[0]
