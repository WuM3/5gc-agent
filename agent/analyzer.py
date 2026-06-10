from __future__ import annotations

from agent.schemas import (
    AnalysisContext,
    ConfigRuleHit,
    FaultCaseHit,
    LogRuleHit,
    QuestionType,
    RouteDecision,
)


LOG_PRIORITY_KEYWORDS = (
    "日志",
    "log",
    "[amf]",
    "[smf]",
    "[upf]",
    "not supported",
    "pfcp",
    "ngap",
    "sctp",
    "connection refused",
    "not found",
    "cannot ping internet",
    "cannot access internet",
    "registered but cannot ping",
    "上传文件",
    "amfcfg",
    "smfcfg",
    "upfcfg",
    "yaml",
    "配置",
)


class Analyzer:
    def __init__(self, knowledge_base, case_base, rule_base, config_rule_base=None):
        self.knowledge_base = knowledge_base
        self.case_base = case_base
        self.rule_base = rule_base
        self.config_rule_base = config_rule_base

    def analyze(
        self,
        question: str,
        question_type: QuestionType,
        route_decision: RouteDecision | None = None,
    ) -> AnalysisContext:
        knowledge_hits = self.knowledge_base.search(question, top_k=3)
        if question_type == QuestionType.KNOWLEDGE:
            knowledge_hits = _prioritize_procedure_hits(knowledge_hits)

        case_hits: list[FaultCaseHit] = []
        rule_hits: list[LogRuleHit] = []
        config_rule_hits: list[ConfigRuleHit] = []

        if question_type == QuestionType.FAULT:
            case_hits = self.case_base.search(question, top_k=3)
            rule_hits = self.rule_base.match(question, top_k=3)
            if self.config_rule_base is not None:
                config_rule_hits = self.config_rule_base.check(question, top_k=5)

        network_functions: list[str] = []
        interfaces: list[str] = []
        possible_causes: list[str] = []
        next_steps: list[str] = []

        if question_type == QuestionType.FAULT and _looks_like_config(question):
            for hit in config_rule_hits:
                _merge_config_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in rule_hits:
                _merge_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in case_hits:
                _merge_case_hit(hit, network_functions, interfaces, possible_causes, next_steps)
        elif question_type == QuestionType.FAULT and _looks_like_log(question):
            for hit in rule_hits:
                _merge_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in config_rule_hits:
                _merge_config_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in case_hits:
                _merge_case_hit(hit, network_functions, interfaces, possible_causes, next_steps)
        else:
            for hit in case_hits:
                _merge_case_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in rule_hits:
                _merge_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)
            for hit in config_rule_hits:
                _merge_config_rule_hit(hit, network_functions, interfaces, possible_causes, next_steps)

        return AnalysisContext(
            question=question,
            question_type=question_type,
            selected_question_type=route_decision.selected_type if route_decision else None,
            detected_question_type=route_decision.detected_type if route_decision else question_type,
            route_warning=route_decision.warning if route_decision else None,
            knowledge_hits=knowledge_hits,
            case_hits=case_hits,
            rule_hits=rule_hits,
            config_rule_hits=config_rule_hits,
            network_functions=network_functions,
            interfaces=interfaces,
            possible_causes=possible_causes,
            next_steps=next_steps,
        )


def _prioritize_procedure_hits(hits):
    return sorted(
        hits,
        key=lambda hit: (hit.source != "procedures.md", -hit.score, hit.title),
    )


def _looks_like_log(question: str) -> bool:
    text = question.casefold()
    return any(keyword in text for keyword in LOG_PRIORITY_KEYWORDS)


def _looks_like_config(question: str) -> bool:
    text = question.casefold()
    return any(
        keyword in text
        for keyword in (
            "上传文件：amfcfg",
            "上传文件：smfcfg",
            "上传文件：upfcfg",
            "amfcfg.yaml",
            "smfcfg.yaml",
            "upfcfg.yaml",
            "配置",
            "config",
        )
    )


def _merge_case_hit(
    hit: FaultCaseHit,
    network_functions: list[str],
    interfaces: list[str],
    possible_causes: list[str],
    next_steps: list[str],
) -> None:
    _extend_unique(network_functions, hit.network_functions)
    _extend_unique(interfaces, hit.interfaces)
    _extend_unique(possible_causes, hit.possible_causes)
    _extend_unique(next_steps, hit.next_steps)


def _merge_rule_hit(
    hit: LogRuleHit,
    network_functions: list[str],
    interfaces: list[str],
    possible_causes: list[str],
    next_steps: list[str],
) -> None:
    _append_unique(network_functions, hit.nf)
    _append_unique(interfaces, hit.interface)
    _extend_unique(possible_causes, hit.possible_causes)
    _extend_unique(next_steps, hit.next_steps)


def _merge_config_rule_hit(
    hit: ConfigRuleHit,
    network_functions: list[str],
    interfaces: list[str],
    possible_causes: list[str],
    next_steps: list[str],
) -> None:
    _append_unique(network_functions, hit.nf)
    _append_unique(interfaces, hit.interface)
    _extend_unique(possible_causes, hit.possible_causes)
    _extend_unique(next_steps, hit.next_steps)


def _extend_unique(items: list[str], candidates: list[str]) -> None:
    for candidate in candidates:
        _append_unique(items, candidate)


def _append_unique(items: list[str], candidate: str) -> None:
    if candidate and candidate not in items:
        items.append(candidate)
