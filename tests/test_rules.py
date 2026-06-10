from pathlib import Path

from agent.analyzer import Analyzer
from agent.schemas import QuestionType
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_log_rule_base_matches_dnn_not_supported_rule():
    rule_base = LogRuleBase(PROJECT_ROOT / "data" / "rules" / "log_rules.yaml")

    hits = rule_base.match("[SMF] DNN internet is not supported")

    assert hits[0].keyword == "DNN not supported"
    assert hits[0].nf == "SMF"
    assert "N11" in hits[0].interface


def test_log_rule_base_matches_n6_route_or_nat_rule():
    rule_base = LogRuleBase(PROJECT_ROOT / "data" / "rules" / "log_rules.yaml")

    hits = rule_base.match("UE can register but cannot ping internet, maybe NAT error on N6")

    assert hits[0].keyword == "N6 route or NAT"
    assert hits[0].nf == "UPF"


def test_analyzer_merges_rule_context_with_retrieval_hits():
    analyzer = Analyzer(
        knowledge_base=KnowledgeBase(PROJECT_ROOT / "data" / "docs"),
        case_base=FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json"),
        rule_base=LogRuleBase(PROJECT_ROOT / "data" / "rules" / "log_rules.yaml"),
    )

    context = analyzer.analyze("SMF 日志 DNN not supported", QuestionType.LOG)

    assert "SMF" in context.network_functions
    assert "N11" in context.interfaces
    assert any("subscriber" in cause.casefold() for cause in context.possible_causes)
    assert context.knowledge_hits
    assert context.case_hits
    assert context.rule_hits
