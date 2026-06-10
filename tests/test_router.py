from agent.router import resolve_question_type, route_question
from agent.schemas import QuestionType


def test_manual_question_type_overrides_auto_detection():
    result = route_question("AMF 的作用是什么？", manual_type="故障诊断")

    assert result == QuestionType.FAULT


def test_routes_log_analysis_from_core_network_log_keywords():
    result = route_question("[SMF] DNN internet is not supported")

    assert result == QuestionType.LOG


def test_routes_fault_diagnosis_from_failure_symptoms():
    result = route_question("UE 注册成功但是不能上网，应该怎么排查？")

    assert result == QuestionType.FAULT


def test_routes_process_question_from_flow_keywords():
    result = route_question("PDU Session 建立流程经过哪些网元？")

    assert result == QuestionType.PROCEDURE


def test_routes_knowledge_question_as_default():
    result = route_question("AMF 和 SMF 的区别是什么？")

    assert result == QuestionType.KNOWLEDGE


def test_resolve_question_type_corrects_mismatched_manual_selection():
    decision = resolve_question_type(
        "UE 注册成功但不能上网，应该怎么排查？",
        manual_type="知识查询",
    )

    assert decision.selected_type == QuestionType.KNOWLEDGE
    assert decision.detected_type == QuestionType.FAULT
    assert decision.final_type == QuestionType.FAULT
    assert decision.mismatch is True
    assert "知识查询" in decision.warning
    assert "故障诊断" in decision.warning


def test_resolve_question_type_keeps_matching_manual_selection():
    decision = resolve_question_type(
        "PDU Session 建立流程经过哪些网元？",
        manual_type="流程解释",
    )

    assert decision.selected_type == QuestionType.PROCEDURE
    assert decision.detected_type == QuestionType.PROCEDURE
    assert decision.final_type == QuestionType.PROCEDURE
    assert decision.mismatch is False
    assert decision.warning is None
