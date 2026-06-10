from pathlib import Path

from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_base_finds_amf_and_smf_snippets():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    hits = kb.search("AMF 和 SMF 的区别是什么？", top_k=4)

    assert any(
        hit.title == "AMF 接入与移动性管理功能" and "AMF" in hit.snippet
        for hit in hits
    )
    assert any(
        hit.title == "SMF 会话管理功能" and "SMF" in hit.snippet
        for hit in hits
    )


def test_knowledge_base_ranks_pdu_session_establishment_first_with_n11():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    hits = kb.search("PDU Session 建立流程")

    assert hits[0].title == "PDU Session Establishment"
    assert "N11" in hits[0].snippet


def test_knowledge_base_finds_general_core_network_question():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    hits = kb.search("什么是核心网", top_k=2)

    assert hits
    assert hits[0].title == "5G 核心网总体架构"
    assert "控制面" in hits[0].snippet
    assert "用户面" in hits[0].snippet


def test_fault_case_base_finds_dnn_not_supported_case():
    case_base = FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json")

    hits = case_base.search("SMF 日志 DNN not supported")

    assert hits[0].case_id == "FC-005"
    assert "SMF" in hits[0].network_functions
    assert "N11" in hits[0].interfaces


def test_fault_case_base_finds_registered_but_no_internet_case():
    case_base = FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json")

    hits = case_base.search("UE 注册成功但不能上网")

    assert hits[0].case_id == "FC-008"
    assert "N6" in hits[0].interfaces


def test_knowledge_base_does_not_match_n1_inside_n11():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    hits = kb.search("N1", top_k=5)

    assert "PDU Session Establishment" not in [hit.title for hit in hits]


def test_fault_case_base_does_not_match_n1_inside_n11():
    case_base = FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json")

    hits = case_base.search("N1", top_k=5)

    assert "FC-005" not in [hit.case_id for hit in hits]


def test_knowledge_base_non_positive_top_k_returns_empty_list():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    assert kb.search("AMF", top_k=0) == []
    assert kb.search("AMF", top_k=-1) == []


def test_fault_case_base_non_positive_top_k_returns_empty_list():
    case_base = FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json")

    assert case_base.search("SMF", top_k=0) == []
    assert case_base.search("SMF", top_k=-1) == []
