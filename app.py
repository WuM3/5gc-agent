from __future__ import annotations

import os

import streamlit as st

from agent.pipeline import AgentPipeline
from agent.report import format_case_hits, format_knowledge_hits, format_rule_hits
from agent.schemas import AgentReport, AnalysisContext, QuestionType
from config import load_env_file


PAGE_TITLE = "面向 5G 核心网的知识查询与故障排查 Agent"
DEFAULT_QUESTION = ""
QUESTION_STATE_KEY = "question"
ACTION_LABELS = {
    QuestionType.AUTO.value: ("生成回答", "回答结果", "正在生成回答..."),
    QuestionType.KNOWLEDGE.value: ("生成知识回答", "知识回答", "正在生成知识回答..."),
    QuestionType.PROCEDURE.value: ("生成流程说明", "流程说明", "正在生成流程说明..."),
    QuestionType.FAULT.value: ("生成诊断报告", "诊断报告", "正在生成诊断报告..."),
    QuestionType.LOG.value: ("分析日志", "日志分析结果", "正在分析日志..."),
}
EXAMPLE_QUESTIONS = {
    QuestionType.AUTO.value: (
        ("核心网概念", "什么是 5G 核心网？"),
        ("PDU 流程", "PDU Session 建立流程经过哪些网元？"),
        ("DNN 日志", "SMF 日志中出现 DNN not supported"),
    ),
    QuestionType.KNOWLEDGE.value: (
        ("核心网概念", "什么是 5G 核心网？"),
        ("AMF 职责", "AMF 的主要作用是什么？"),
        ("AMF/SMF 区别", "AMF 和 SMF 的区别是什么？"),
    ),
    QuestionType.PROCEDURE.value: (
        ("UE 注册", "UE Registration 流程包括哪些步骤？"),
        ("PDU 会话", "PDU Session 建立流程经过哪些网元？"),
        ("N4 建立", "N4 Session Establishment 的作用是什么？"),
    ),
    QuestionType.FAULT.value: (
        ("不能上网", "UE 注册成功但不能上网，应该怎么排查？"),
        ("N4 失败", "SMF 与 UPF 之间 N4 Session Establishment 失败"),
        ("鉴权失败", "UE Registration 被拒绝并且 AMF 显示鉴权失败"),
    ),
    QuestionType.LOG.value: (
        ("DNN 日志", "SMF 日志中出现 DNN not supported"),
        ("切片不匹配", "SMF 日志出现 S-NSSAI mismatch"),
        ("PFCP 失败", "UPF 日志出现 PFCP session failure"),
    ),
}


def _api_key_status() -> str:
    return "已配置" if os.getenv("LLM_API_KEY", "").strip() else "未配置"


def action_labels(question_type: str) -> tuple[str, str, str]:
    return ACTION_LABELS.get(question_type, ACTION_LABELS[QuestionType.AUTO.value])


def example_questions(question_type: str) -> tuple[tuple[str, str], ...]:
    return EXAMPLE_QUESTIONS.get(question_type, EXAMPLE_QUESTIONS[QuestionType.AUTO.value])


def evidence_counts(context: AnalysisContext) -> dict[str, int]:
    return {
        "knowledge": len(context.knowledge_hits),
        "cases": len(context.case_hits),
        "rules": len(context.rule_hits),
    }


def build_export_markdown(report: AgentReport) -> str:
    lines = [
        "# 5G 核心网 Agent 分析结果",
        "",
        f"- 运行模式：{report.mode}",
        f"- 问题类型：{report.context.question_type.value}",
        f"- 用户问题：{report.context.question}",
    ]
    if report.llm_error:
        lines.append(f"- 降级原因：{report.llm_error}")

    lines.extend(
        [
            "",
            "## 回答",
            report.content,
            "",
            "## 命中的知识片段",
            format_knowledge_hits(report.context),
            "",
            "## 命中的故障案例",
            format_case_hits(report.context),
            "",
            "## 命中的日志规则",
            format_rule_hits(report.context),
            "",
        ]
    )
    return "\n".join(lines)


def _ensure_question_state() -> None:
    if QUESTION_STATE_KEY not in st.session_state:
        st.session_state[QUESTION_STATE_KEY] = DEFAULT_QUESTION


def _render_example_buttons(question_type: str) -> None:
    examples = example_questions(question_type)
    cols = st.columns(len(examples))
    for index, (label, question) in enumerate(examples):
        if cols[index].button(label, use_container_width=True, help=question):
            st.session_state[QUESTION_STATE_KEY] = question
            st.rerun()


def main() -> None:
    load_env_file()
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)
    _ensure_question_state()

    st.sidebar.header("运行配置")
    st.sidebar.write(f"LLM Provider：{os.getenv('LLM_PROVIDER', 'openai_compatible')}")
    st.sidebar.write(f"LLM Model：{os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    st.sidebar.write(f"API Key：{_api_key_status()}")
    st.sidebar.caption("在线模式优先；缺少 API Key 或在线调用失败时，将自动降级为离线兜底模式。")

    question_type = st.selectbox(
        "问题类型",
        [question_type.value for question_type in QuestionType],
    )
    _render_example_buttons(question_type)
    question = st.text_area(
        "问题描述",
        key=QUESTION_STATE_KEY,
        placeholder="请输入 5G 核心网知识、流程、故障或日志问题",
    )
    button_label, selected_report_title, spinner_text = action_labels(question_type)

    if st.button(button_label, type="primary"):
        stripped_question = question.strip()
        if not stripped_question:
            st.warning("请输入问题描述。")
            return

        with st.spinner(spinner_text):
            report = AgentPipeline().run(stripped_question, manual_type=question_type)

        if report.mode == "online":
            st.success("在线模式")
        else:
            st.success("离线兜底模式")

        if report.llm_error:
            st.info(f"降级原因：{report.llm_error}")

        report_col, evidence_col = st.columns(2)
        report_title = selected_report_title
        if question_type == QuestionType.AUTO.value:
            _, report_title, _ = action_labels(report.context.question_type.value)

        with report_col:
            st.subheader(report_title)
            st.markdown(report.content)

        with evidence_col:
            st.subheader("证据区")
            counts = evidence_counts(report.context)
            metric_cols = st.columns(3)
            metric_cols[0].metric("知识片段", counts["knowledge"])
            metric_cols[1].metric("故障案例", counts["cases"])
            metric_cols[2].metric("日志规则", counts["rules"])
            with st.expander("命中的知识片段", expanded=True):
                st.text(format_knowledge_hits(report.context))
            with st.expander("命中的故障案例"):
                st.text(format_case_hits(report.context))
            with st.expander("命中的日志规则"):
                st.text(format_rule_hits(report.context))

        st.download_button(
            "下载 Markdown 报告",
            data=build_export_markdown(report),
            file_name="5gc-agent-report.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
