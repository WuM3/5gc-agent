from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestionType(str, Enum):
    AUTO = "自动识别"
    KNOWLEDGE = "知识查询"
    PROCEDURE = "流程解释"
    FAULT = "故障诊断"
    LOG = "日志分析"


@dataclass(frozen=True)
class KnowledgeHit:
    title: str
    source: str
    snippet: str
    score: int


@dataclass(frozen=True)
class FaultCaseHit:
    case_id: str
    title: str
    issue_type: str
    symptoms: list[str]
    network_functions: list[str]
    interfaces: list[str]
    possible_causes: list[str]
    next_steps: list[str]
    evidence: str
    score: int


@dataclass(frozen=True)
class LogRuleHit:
    keyword: str
    nf: str
    interface: str
    possible_causes: list[str]
    next_steps: list[str]
    severity: str
    score: int


@dataclass(frozen=True)
class AnalysisContext:
    question: str
    question_type: QuestionType
    knowledge_hits: list[KnowledgeHit] = field(default_factory=list)
    case_hits: list[FaultCaseHit] = field(default_factory=list)
    rule_hits: list[LogRuleHit] = field(default_factory=list)
    network_functions: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    possible_causes: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LLMResult:
    content: str
    mode: str
    error: str | None = None


@dataclass(frozen=True)
class AgentReport:
    content: str
    mode: str
    context: AnalysisContext
    llm_error: str | None = None
