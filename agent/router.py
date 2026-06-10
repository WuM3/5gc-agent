from __future__ import annotations

from agent.schemas import QuestionType, RouteDecision


MANUAL_TYPE_MAP = {
    QuestionType.AUTO.value: None,
    QuestionType.KNOWLEDGE.value: QuestionType.KNOWLEDGE,
    QuestionType.FAULT.value: QuestionType.FAULT,
    # Backward-compatible aliases for reports, tests, or old UI state.
    "知识/流程查询": QuestionType.KNOWLEDGE,
    "流程解释": QuestionType.KNOWLEDGE,
    "故障/日志分析": QuestionType.FAULT,
    "故障诊断": QuestionType.FAULT,
    "日志分析": QuestionType.FAULT,
}

LOG_KEYWORDS = (
    "日志",
    "log",
    "[amf]",
    "[smf]",
    "[upf]",
    "dnn",
    "not supported",
    "pfcp",
    "ngap",
    "sctp",
    "cannot ping internet",
    "connection refused",
    "not found",
)
FAULT_KEYWORDS = (
    "失败",
    "异常",
    "不能",
    "无法",
    "排查",
    "故障",
    "ping",
    "不通",
    "注册成功但是",
    "配置",
    "配置文件",
    "amfcfg",
    "smfcfg",
    "upfcfg",
    "yaml",
    "json",
)
PROCEDURE_KEYWORDS = ("流程", "建立", "registration", "procedure", "经过哪些", "步骤")


def route_question(question: str, manual_type: str | None = None) -> QuestionType:
    if manual_type:
        selected = MANUAL_TYPE_MAP.get(manual_type)
        if selected:
            return selected

    return detect_question_type(question)


def detect_question_type(question: str) -> QuestionType:
    text = question.lower()

    if any(keyword in text for keyword in LOG_KEYWORDS):
        return QuestionType.FAULT
    if any(keyword in text for keyword in FAULT_KEYWORDS):
        return QuestionType.FAULT
    if any(keyword in text for keyword in PROCEDURE_KEYWORDS):
        return QuestionType.KNOWLEDGE
    return QuestionType.KNOWLEDGE


def resolve_question_type(question: str, manual_type: str | None = None) -> RouteDecision:
    selected = MANUAL_TYPE_MAP.get(manual_type) if manual_type else None
    detected = detect_question_type(question)

    if selected is None:
        return RouteDecision(
            selected_type=None,
            detected_type=detected,
            final_type=detected,
        )

    if selected == detected:
        return RouteDecision(
            selected_type=selected,
            detected_type=detected,
            final_type=selected,
        )

    warning = (
        f"你选择了“{selected.value}”，但系统判断该问题更像“{detected.value}”，"
        f"已按“{detected.value}”处理。"
    )
    return RouteDecision(
        selected_type=selected,
        detected_type=detected,
        final_type=detected,
        mismatch=True,
        warning=warning,
    )
