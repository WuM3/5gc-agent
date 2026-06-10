import json
from pathlib import Path

import yaml

from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_fault_case_library_contains_course_mvp_scale():
    cases_path = PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    assert len(cases) >= 12


def test_evaluation_set_contains_twenty_demo_questions():
    eval_path = PROJECT_ROOT / "data" / "evaluation" / "test_questions.json"
    questions = json.loads(eval_path.read_text(encoding="utf-8"))

    assert len(questions) >= 20
    assert {"knowledge", "procedure", "fault", "log"} <= {
        item["type"] for item in questions
    }


def test_knowledge_library_covers_design_network_functions():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    for query, expected_title in [
        ("AUSF 和 UDM 的作用", "AUSF 与 UDM 鉴权和用户数据"),
        ("PCF 策略控制", "PCF 策略控制功能"),
        ("NSSF 切片选择", "NSSF 切片选择功能"),
        ("N1 N2 N3 N4 N6 接口", "5G 核心网关键接口"),
    ]:
        hits = kb.search(query, top_k=5)
        assert expected_title in [hit.title for hit in hits]


def test_procedure_library_covers_design_procedures():
    kb = KnowledgeBase(PROJECT_ROOT / "data" / "docs")

    for query, expected_title in [
        ("Service Request 流程", "Service Request"),
        ("Deregistration 注销流程", "Deregistration"),
        ("NRF Registration Discovery 流程", "NRF Registration and Discovery"),
    ]:
        hits = kb.search(query, top_k=5)
        assert expected_title in [hit.title for hit in hits]


def test_fault_case_library_covers_design_faults():
    case_base = FaultCaseBase(PROJECT_ROOT / "data" / "fault_cases" / "fault_cases.json")

    for query, expected_case_id in [
        ("AMF 无法注册到 NRF", "FC-003"),
        ("SMF 无法发现 UPF", "FC-004"),
        ("gNB 连不上 AMF SCTP", "FC-011"),
        ("MongoDB 用户数据缺失", "FC-013"),
        ("WebConsole subscriber 配置错误", "FC-014"),
        ("DNS IP 地址配置错误", "FC-015"),
    ]:
        hits = case_base.search(query, top_k=5)
        assert expected_case_id in [hit.case_id for hit in hits]


def test_log_rule_library_covers_core_logs():
    rule_base = LogRuleBase(PROJECT_ROOT / "data" / "rules" / "log_rules.yaml")

    for log_text, expected_keyword in [
        ("[AMF] NRF discovery failed for AUSF service", "NRF discovery failure"),
        ("[AMF] NGAP SCTP connection refused by gNB", "NGAP SCTP connection failure"),
        ("[SMF] MongoDB subscriber data not found", "Subscriber data missing"),
    ]:
        hits = rule_base.match(log_text)
        assert hits
        assert hits[0].keyword == expected_keyword


def test_log_rule_library_has_mvp_scale():
    rules_path = PROJECT_ROOT / "data" / "rules" / "log_rules.yaml"
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

    assert len(data["rules"]) >= 8
