from __future__ import annotations

from agent.schemas import (
    AgentReport,
    AnalysisContext,
    FaultCaseHit,
    KnowledgeHit,
    LLMResult,
    LogRuleHit,
    QuestionType,
)


PROMPT_TASKS = {
    QuestionType.KNOWLEDGE: "请输出知识回答，包含概念解释、关键网元或接口、参考依据。",
    QuestionType.PROCEDURE: "请输出流程说明，包含主要步骤、涉及网元、涉及接口和参考依据。",
    QuestionType.FAULT: "请输出诊断报告，包含诊断结论、可能原因、建议排查步骤和参考依据。",
    QuestionType.LOG: "请输出日志分析结果，包含日志含义、涉及网元或接口、可能原因、建议排查步骤和参考依据。",
}


class ReportGenerator:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate(self, context: AnalysisContext) -> AgentReport:
        llm_result = self.llm_client.generate(build_prompt(context))
        if llm_result.content.strip():
            return AgentReport(
                content=llm_result.content,
                mode=llm_result.mode,
                context=context,
                llm_error=llm_result.error,
            )

        return AgentReport(
            content=build_offline_report(context, llm_result),
            mode="offline",
            context=context,
            llm_error=llm_result.error,
        )


def build_prompt(context: AnalysisContext) -> str:
    return (
        "你是 5G Core 知识查询与故障排查助手。请基于给定证据生成结构化中文回答。\n"
        "在线模式必须严格依据命中的知识、案例和日志规则作答，避免编造证据之外的事实。\n\n"
        f"用户问题：{context.question}\n"
        f"问题类型：{context.question_type.value}\n\n"
        "命中的知识片段\n"
        f"{format_knowledge_hits(context.knowledge_hits)}\n\n"
        "命中的故障案例\n"
        f"{format_case_hits(context.case_hits)}\n\n"
        "命中的日志规则\n"
        f"{format_rule_hits(context.rule_hits)}\n\n"
        f"{_prompt_task(context.question_type)}"
    )


def build_offline_report(
    context: AnalysisContext,
    llm_result: LLMResult | None = None,
) -> str:
    if context.question_type == QuestionType.KNOWLEDGE:
        return "\n".join(
            [
                f"问题类型：{context.question_type.value}",
                f"知识回答：{_knowledge_answer(context)}",
                f"参考依据：{_references(context)}",
                "运行模式：offline",
                f"降级原因：{_downgrade_reason(llm_result)}",
            ]
        )

    if context.question_type == QuestionType.PROCEDURE:
        return "\n".join(
            [
                f"问题类型：{context.question_type.value}",
                f"流程说明：{_knowledge_answer(context)}",
                f"涉及网元：{_join_values(context.network_functions, '请结合流程片段识别')}",
                f"涉及接口：{_join_values(context.interfaces, '请结合流程片段识别')}",
                f"参考依据：{_references(context)}",
                "运行模式：offline",
                f"降级原因：{_downgrade_reason(llm_result)}",
            ]
        )

    if context.question_type == QuestionType.LOG:
        return "\n".join(
            [
                f"问题类型：{context.question_type.value}",
                f"涉及网元：{_join_values(context.network_functions, '未识别明确网元')}",
                f"涉及接口：{_join_values(context.interfaces, '未识别明确接口')}",
                f"日志分析结果：{_diagnosis(context)}",
                f"可能原因：{_join_values(context.possible_causes, '暂无明确原因')}",
                f"建议排查步骤：{_numbered_values(context.next_steps, '暂无明确步骤')}",
                f"参考依据：{_references(context)}",
                "运行模式：offline",
                f"降级原因：{_downgrade_reason(llm_result)}",
            ]
        )

    return "\n".join(
        [
            f"问题类型：{context.question_type.value}",
            f"涉及网元：{_join_values(context.network_functions, '未识别明确网元')}",
            f"涉及接口：{_join_values(context.interfaces, '未识别明确接口')}",
            f"诊断结论：{_diagnosis(context)}",
            f"可能原因：{_join_values(context.possible_causes, '暂无明确原因')}",
            f"建议排查步骤：{_numbered_values(context.next_steps, '暂无明确步骤')}",
            f"参考依据：{_references(context)}",
            "运行模式：offline",
            f"降级原因：{_downgrade_reason(llm_result)}",
        ]
    )


def format_knowledge_hits(source: AnalysisContext | list[KnowledgeHit]) -> str:
    hits = source.knowledge_hits if isinstance(source, AnalysisContext) else source
    if not hits:
        return "未命中知识片段"

    lines: list[str] = []
    for index, hit in enumerate(hits, start=1):
        lines.append(
            f"{index}. {hit.title}（来源：{hit.source}，分数：{hit.score}）\n"
            f"   摘要：{hit.snippet}"
        )
    return "\n".join(lines)


def format_case_hits(source: AnalysisContext | list[FaultCaseHit]) -> str:
    hits = source.case_hits if isinstance(source, AnalysisContext) else source
    if not hits:
        return "未命中故障案例"

    lines: list[str] = []
    for index, hit in enumerate(hits, start=1):
        lines.append(
            f"{index}. {hit.case_id} {hit.title}（类型：{hit.issue_type}，分数：{hit.score}）\n"
            f"   症状：{_join_values(hit.symptoms, '未提供')}\n"
            f"   网元：{_join_values(hit.network_functions, '未提供')}\n"
            f"   接口：{_join_values(hit.interfaces, '未提供')}\n"
            f"   可能原因：{_join_values(hit.possible_causes, '未提供')}\n"
            f"   建议步骤：{_join_values(hit.next_steps, '未提供')}\n"
            f"   证据：{hit.evidence or '未提供'}"
        )
    return "\n".join(lines)


def format_rule_hits(source: AnalysisContext | list[LogRuleHit]) -> str:
    hits = source.rule_hits if isinstance(source, AnalysisContext) else source
    if not hits:
        return "未命中日志规则"

    lines: list[str] = []
    for index, hit in enumerate(hits, start=1):
        lines.append(
            f"{index}. {hit.keyword}（网元：{hit.nf}，接口：{hit.interface}，"
            f"严重级别：{hit.severity}，分数：{hit.score}）\n"
            f"   可能原因：{_join_values(hit.possible_causes, '未提供')}\n"
            f"   建议步骤：{_join_values(hit.next_steps, '未提供')}"
        )
    return "\n".join(lines)


def _diagnosis(context: AnalysisContext) -> str:
    if context.question_type == QuestionType.LOG and context.rule_hits:
        hit = context.rule_hits[0]
        return f"优先匹配日志规则：{hit.keyword}"
    if context.case_hits:
        hit = context.case_hits[0]
        return f"优先匹配故障案例 {hit.case_id}：{hit.title}"
    if context.rule_hits:
        hit = context.rule_hits[0]
        return f"优先匹配日志规则：{hit.keyword}"
    if context.knowledge_hits:
        return _knowledge_answer(context)
    return "未命中明确证据，建议补充日志、接口消息或现象描述"


def _knowledge_answer(context: AnalysisContext) -> str:
    if not context.knowledge_hits:
        return "未命中明确知识片段，建议补充网元、接口或流程关键词"
    hit = context.knowledge_hits[0]
    return f"{hit.title}：{hit.snippet}"


def _prompt_task(question_type: QuestionType) -> str:
    return PROMPT_TASKS.get(question_type, "请输出回答，包含结论、依据和建议。")


def _references(context: AnalysisContext) -> str:
    references: list[str] = []
    references.extend(
        f"知识：{hit.source}/{hit.title}" for hit in context.knowledge_hits
    )
    references.extend(
        f"案例：{hit.case_id}/{hit.title}" for hit in context.case_hits
    )
    references.extend(
        f"规则：{hit.keyword}/{hit.nf}/{hit.interface}" for hit in context.rule_hits
    )
    return _join_values(references, "未命中参考依据")


def _downgrade_reason(llm_result: LLMResult | None) -> str:
    if llm_result is None:
        return "未调用在线模型"
    return llm_result.error or "在线模型未返回内容"


def _join_values(values: list[str], empty_text: str) -> str:
    return "、".join(value for value in values if value) or empty_text


def _numbered_values(values: list[str], empty_text: str) -> str:
    filtered = [value for value in values if value]
    if not filtered:
        return empty_text
    return "；".join(f"{index}. {value}" for index, value in enumerate(filtered, start=1))
