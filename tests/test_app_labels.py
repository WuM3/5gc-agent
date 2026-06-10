from agent.schemas import AgentReport, AnalysisContext, KnowledgeHit, QuestionType
from app import (
    DEFAULT_QUESTION,
    action_labels,
    build_export_markdown,
    evidence_counts,
    example_questions,
)


def test_action_labels_change_for_selected_question_type():
    assert action_labels("知识查询") == ("生成知识回答", "知识回答", "正在生成知识回答...")
    assert action_labels("流程解释") == ("生成流程说明", "流程说明", "正在生成流程说明...")
    assert action_labels("故障诊断") == ("生成诊断报告", "诊断报告", "正在生成诊断报告...")
    assert action_labels("日志分析") == ("分析日志", "日志分析结果", "正在分析日志...")


def test_action_labels_fall_back_to_general_answer_for_auto_type():
    assert action_labels("自动识别") == ("生成回答", "回答结果", "正在生成回答...")


def test_question_input_default_is_empty():
    assert DEFAULT_QUESTION == ""


def test_example_questions_change_with_selected_question_type():
    knowledge_examples = example_questions("知识查询")
    log_examples = example_questions("日志分析")

    assert knowledge_examples
    assert log_examples
    assert knowledge_examples != log_examples
    assert any("AMF" in question for _, question in knowledge_examples)
    assert any("DNN" in question for _, question in log_examples)


def test_evidence_counts_report_hit_totals():
    context = AnalysisContext(
        question="AMF 是什么？",
        question_type=QuestionType.KNOWLEDGE,
        knowledge_hits=[
            KnowledgeHit(
                title="AMF 接入与移动性管理功能",
                source="core_network.md",
                snippet="AMF 负责 UE 注册和移动性管理。",
                score=10,
            )
        ],
    )

    assert evidence_counts(context) == {
        "knowledge": 1,
        "cases": 0,
        "rules": 0,
    }


def test_build_export_markdown_includes_answer_and_evidence_sections():
    context = AnalysisContext(
        question="AMF 是什么？",
        question_type=QuestionType.KNOWLEDGE,
        knowledge_hits=[
            KnowledgeHit(
                title="AMF 接入与移动性管理功能",
                source="core_network.md",
                snippet="AMF 负责 UE 注册和移动性管理。",
                score=10,
            )
        ],
    )
    report = AgentReport(
        content="AMF 负责接入和移动性管理。",
        mode="online",
        context=context,
    )

    markdown = build_export_markdown(report)

    assert "# 5G 核心网 Agent 分析结果" in markdown
    assert "AMF 负责接入和移动性管理。" in markdown
    assert "## 命中的知识片段" in markdown
    assert "## 命中的故障案例" in markdown
    assert "## 命中的日志规则" in markdown
