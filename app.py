from __future__ import annotations

import os
import re

import streamlit as st

from agent.pipeline import AgentPipeline
from agent.report import (
    format_case_hits,
    format_config_rule_hits,
    format_knowledge_hits,
    format_rule_hits,
)
from agent.schemas import AgentReport, AnalysisContext, QuestionType
from config import load_env_file


PAGE_TITLE = "面向 5G 核心网的知识查询与故障排查 Agent"
DEFAULT_QUESTION = ""
QUESTION_STATE_KEY = "question"
SHOW_EXAMPLE_BUTTONS = False
MAX_UPLOAD_CHARS = 12000
UPLOAD_ACCEPTED_TYPES = ["log", "txt", "json", "yaml", "yml"]
ACTION_LABELS = {
    QuestionType.AUTO.value: ("生成回答", "回答结果", "正在生成回答..."),
    QuestionType.KNOWLEDGE.value: ("生成查询回答", "知识回答", "正在生成查询回答..."),
    QuestionType.FAULT.value: ("生成分析报告", "故障分析报告", "正在生成分析报告..."),
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
        ("PDU 会话", "PDU Session 建立流程经过哪些网元？"),
    ),
    QuestionType.FAULT.value: (
        ("不能上网", "UE 注册成功但不能上网，应该怎么排查？"),
        ("DNN 日志", "SMF 日志中出现 DNN not supported"),
        ("PFCP 失败", "UPF 日志出现 PFCP session failure"),
    ),
}


def _api_key_status() -> str:
    return "已配置" if os.getenv("LLM_API_KEY", "").strip() else "未配置"


def action_labels(question_type: str) -> tuple[str, str, str]:
    return ACTION_LABELS.get(question_type, ACTION_LABELS[QuestionType.AUTO.value])


def question_type_options() -> list[str]:
    return [question_type.value for question_type in QuestionType]


def example_questions(question_type: str) -> tuple[tuple[str, str], ...]:
    return EXAMPLE_QUESTIONS.get(question_type, EXAMPLE_QUESTIONS[QuestionType.AUTO.value])


def decode_uploaded_bytes(
    content: bytes,
    max_chars: int = MAX_UPLOAD_CHARS,
) -> tuple[str, str | None]:
    warning = None
    for encoding in ("utf-8", "gbk"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("utf-8", errors="replace")

    text = text.replace("\x00", "").strip()
    if len(text) > max_chars:
        text = text[:max_chars]
        warning = f"上传文件内容较长，已截取前 {max_chars} 个字符用于分析。"
    return text, warning


def build_user_input(
    question: str,
    uploaded_text: str | None = None,
    uploaded_filename: str | None = None,
) -> str:
    parts: list[str] = []
    stripped_question = question.strip()
    if stripped_question:
        parts.append(stripped_question)

    if uploaded_text and uploaded_text.strip():
        filename = uploaded_filename or "uploaded-file"
        parts.append(f"上传文件：{filename}\n{uploaded_text.strip()}")

    return "\n\n".join(parts)


def evidence_counts(context: AnalysisContext) -> dict[str, int]:
    return {
        "knowledge": len(context.knowledge_hits),
        "cases": len(context.case_hits),
        "rules": len(context.rule_hits),
        "configs": len(context.config_rule_hits),
    }


def route_summary_items(context: AnalysisContext) -> dict[str, str]:
    items = {
        "用户选择": (
            context.selected_question_type.value
            if context.selected_question_type
            else QuestionType.AUTO.value
        ),
        "系统识别": (
            context.detected_question_type.value
            if context.detected_question_type
            else context.question_type.value
        ),
        "最终采用": context.question_type.value,
    }
    if context.route_warning:
        items["纠偏提示"] = context.route_warning
    return items


def route_summary_caption(context: AnalysisContext) -> str:
    items = route_summary_items(context)
    parts = [
        f"用户选择：{items['用户选择']}",
        f"系统识别：{items['系统识别']}",
        f"最终采用：{items['最终采用']}",
    ]
    if "纠偏提示" in items:
        parts.append(f"提示：{items['纠偏提示']}")
    return "；".join(parts)


def display_report_content(report_title: str, content: str) -> str:
    stripped_content = content.strip()
    lines = stripped_content.splitlines()
    if not lines:
        return stripped_content

    first_line = lines[0].strip()
    heading_text = re.sub(r"^#+\s*", "", first_line).strip()
    if heading_text == report_title:
        return "\n".join(lines[1:]).lstrip()
    return stripped_content


def build_export_markdown(report: AgentReport) -> str:
    lines = [
        "# 5G 核心网 Agent 分析结果",
        "",
        f"- 运行模式：{report.mode}",
        f"- 问题类型：{report.context.question_type.value}",
        f"- 用户问题：{report.context.question}",
    ]
    if report.context.selected_question_type:
        lines.append(f"- 用户选择类型：{report.context.selected_question_type.value}")
    if report.context.detected_question_type:
        lines.append(f"- 系统识别类型：{report.context.detected_question_type.value}")
    if report.context.route_warning:
        lines.append(f"- 模式提示：{report.context.route_warning}")
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
            "## 命中的配置规则",
            format_config_rule_hits(report.context),
            "",
        ]
    )
    return "\n".join(lines)


def _ensure_question_state() -> None:
    if QUESTION_STATE_KEY not in st.session_state:
        st.session_state[QUESTION_STATE_KEY] = DEFAULT_QUESTION


def _render_example_buttons(question_type: str) -> None:
    if not SHOW_EXAMPLE_BUTTONS:
        return
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
    st.sidebar.caption("在线模式优先；缺少 API Key 或在线调用失败时，将自动切换为离线模式。")

    question_type = st.selectbox(
        "问题类型",
        question_type_options(),
    )
    _render_example_buttons(question_type)
    question = st.text_area(
        "问题描述",
        key=QUESTION_STATE_KEY,
        placeholder="请输入 5G 核心网知识、流程、故障、日志或配置问题",
    )
    button_label, selected_report_title, spinner_text = action_labels(question_type)

    control_cols = st.columns([1.2, 1, 5])
    with control_cols[0]:
        run_clicked = st.button(button_label, type="primary", use_container_width=True)
    with control_cols[1]:
        with st.popover("上传文件", use_container_width=True):
            uploaded_file = st.file_uploader(
                "选择日志/文本文件",
                type=UPLOAD_ACCEPTED_TYPES,
                accept_multiple_files=False,
                help="支持上传日志、JSON 或 YAML 文本文件；文件内容会和问题描述一起分析。",
            )

    uploaded_text = None
    if uploaded_file is not None:
        uploaded_text, upload_warning = decode_uploaded_bytes(uploaded_file.getvalue())
        st.caption(f"已读取上传文件：{uploaded_file.name}")
        if upload_warning:
            st.warning(upload_warning)

    if run_clicked:
        user_input = build_user_input(
            question,
            uploaded_text=uploaded_text,
            uploaded_filename=uploaded_file.name if uploaded_file is not None else None,
        )
        if not user_input:
            st.warning("请输入问题描述，或上传日志/文本文件。")
            return

        with st.spinner(spinner_text):
            report = AgentPipeline().run(user_input, manual_type=question_type)

        if report.mode == "online":
            st.success("在线模式")
        else:
            st.success("离线模式")

        if report.llm_error:
            st.info(f"降级原因：{report.llm_error}")

        report_col, evidence_col = st.columns(2)
        report_title = selected_report_title
        if question_type == QuestionType.AUTO.value:
            _, report_title, _ = action_labels(report.context.question_type.value)

        with report_col:
            st.subheader(report_title)
            st.markdown(display_report_content(report_title, report.content))
            st.caption(route_summary_caption(report.context))

        with evidence_col:
            st.subheader("证据区")
            counts = evidence_counts(report.context)
            metric_cols = st.columns(4)
            metric_cols[0].metric("知识片段", counts["knowledge"])
            metric_cols[1].metric("故障案例", counts["cases"])
            metric_cols[2].metric("日志规则", counts["rules"])
            metric_cols[3].metric("配置规则", counts["configs"])
            with st.expander("命中的知识片段", expanded=True):
                st.text(format_knowledge_hits(report.context))
            with st.expander("命中的故障案例"):
                st.text(format_case_hits(report.context))
            with st.expander("命中的日志规则"):
                st.text(format_rule_hits(report.context))
            with st.expander("命中的配置规则"):
                st.text(format_config_rule_hits(report.context))

        st.download_button(
            "下载 Markdown 报告",
            data=build_export_markdown(report),
            file_name="5gc-agent-report.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
