from agent.schemas import AgentReport, AnalysisContext, ConfigRuleHit, KnowledgeHit, QuestionType
from app import (
    DEFAULT_QUESTION,
    MAX_UPLOAD_CHARS,
    SHOW_EXAMPLE_BUTTONS,
    UPLOAD_ACCEPTED_TYPES,
    action_labels,
    build_export_markdown,
    build_user_input,
    decode_uploaded_bytes,
    display_report_content,
    evidence_counts,
    example_questions,
    route_summary_caption,
    question_type_options,
    route_summary_items,
)


def test_action_labels_change_for_selected_question_type():
    assert action_labels("知识查询") == ("生成查询回答", "知识回答", "正在生成查询回答...")
    assert action_labels("故障分析") == ("生成分析报告", "故障分析报告", "正在生成分析报告...")


def test_action_labels_fall_back_to_general_answer_for_auto_type():
    assert action_labels("自动识别") == ("生成回答", "回答结果", "正在生成回答...")


def test_question_type_options_are_merged_modes():
    assert question_type_options() == ["自动识别", "知识查询", "故障分析"]


def test_upload_accepted_types_are_text_or_log_formats():
    assert UPLOAD_ACCEPTED_TYPES == ["log", "txt", "json", "yaml", "yml"]


def test_question_input_default_is_empty():
    assert DEFAULT_QUESTION == ""


def test_example_questions_change_with_selected_question_type():
    knowledge_examples = example_questions("知识查询")
    log_examples = example_questions("故障分析")

    assert knowledge_examples
    assert log_examples
    assert knowledge_examples != log_examples
    assert any("AMF" in question for _, question in knowledge_examples)
    assert any("DNN" in question for _, question in log_examples)


def test_example_buttons_are_not_shown_by_default():
    assert SHOW_EXAMPLE_BUTTONS is False


def test_evidence_counts_report_hit_totals():
    context = AnalysisContext(
        question="AMF 是什么？",
        question_type=QuestionType.KNOWLEDGE,
        knowledge_hits=[
            KnowledgeHit(
                title="AMF 接入与移动性管理功能",
                source="core_network.md",
                snippet="AMF 负责 UE 注册和移动性管理。",
                score=10,
            )
        ],
    )

    assert evidence_counts(context) == {
        "knowledge": 1,
        "cases": 0,
        "rules": 0,
        "configs": 0,
    }


def test_build_export_markdown_includes_answer_and_evidence_sections():
    context = AnalysisContext(
        question="AMF 是什么？",
        question_type=QuestionType.KNOWLEDGE,
        selected_question_type=QuestionType.FAULT,
        detected_question_type=QuestionType.KNOWLEDGE,
        route_warning="你选择了“故障分析”，但系统判断该问题更像“知识查询”，已按“知识查询”处理。",
        knowledge_hits=[
            KnowledgeHit(
                title="AMF 接入与移动性管理功能",
                source="core_network.md",
                snippet="AMF 负责 UE 注册和移动性管理。",
                score=10,
            )
        ],
        config_rule_hits=[
            ConfigRuleHit(
                rule_id="CFG-AMF-001",
                title="AMF N2/NGAP 监听地址缺失",
                nf="AMF",
                interface="N2/NGAP",
                severity="high",
                missing_items=["NGAP 监听地址"],
                possible_causes=["amfcfg.yaml 未配置 ngapIpList"],
                next_steps=["检查 AMF N2 地址是否和 gNB 配置一致"],
                evidence="amfcfg.yaml",
                score=80,
            )
        ],
    )
    report = AgentReport(
        content="AMF 负责接入和移动性管理。",
        mode="online",
        context=context,
    )

    markdown = build_export_markdown(report)

    assert "# 5G 核心网 Agent 分析结果" in markdown
    assert "AMF 负责接入和移动性管理。" in markdown
    assert "系统识别类型：知识查询" in markdown
    assert "用户选择类型：故障分析" in markdown
    assert "模式提示" in markdown
    assert "## 命中的知识片段" in markdown
    assert "## 命中的故障案例" in markdown
    assert "## 命中的日志规则" in markdown
    assert "## 命中的配置规则" in markdown
    assert "CFG-AMF-001" in markdown


def test_route_summary_items_include_selected_detected_and_final_type():
    context = AnalysisContext(
        question="AMF 是什么？",
        question_type=QuestionType.KNOWLEDGE,
        selected_question_type=QuestionType.FAULT,
        detected_question_type=QuestionType.KNOWLEDGE,
        route_warning="你选择了“故障分析”，但系统判断该问题更像“知识查询”，已按“知识查询”处理。",
    )

    assert route_summary_items(context) == {
        "用户选择": "故障分析",
        "系统识别": "知识查询",
        "最终采用": "知识查询",
        "纠偏提示": "你选择了“故障分析”，但系统判断该问题更像“知识查询”，已按“知识查询”处理。",
    }


def test_route_summary_caption_is_compact_text_for_report_footer():
    context = AnalysisContext(
        question="UE 不能上网",
        question_type=QuestionType.FAULT,
        selected_question_type=None,
        detected_question_type=QuestionType.FAULT,
    )

    assert route_summary_caption(context) == "用户选择：自动识别；系统识别：故障分析；最终采用：故障分析"


def test_display_report_content_removes_duplicate_leading_title():
    content = "# 故障分析报告\n\n诊断结论：UPF N6 路由缺失。"

    assert display_report_content("故障分析报告", content) == "诊断结论：UPF N6 路由缺失。"


def test_display_report_content_keeps_non_duplicate_content():
    content = "诊断结论：UPF N6 路由缺失。"

    assert display_report_content("故障分析报告", content) == content


def test_decode_uploaded_bytes_accepts_utf8_and_truncates_long_text():
    content = ("[SMF] DNN not supported\n" * 2000).encode("utf-8")

    text, warning = decode_uploaded_bytes(content, max_chars=MAX_UPLOAD_CHARS)

    assert text.startswith("[SMF] DNN not supported")
    assert len(text) <= MAX_UPLOAD_CHARS
    assert warning == f"上传文件内容较长，已截取前 {MAX_UPLOAD_CHARS} 个字符用于分析。"


def test_decode_uploaded_bytes_falls_back_to_gbk():
    content = "日志：鉴权失败".encode("gbk")

    text, warning = decode_uploaded_bytes(content)

    assert text == "日志：鉴权失败"
    assert warning is None


def test_build_user_input_combines_description_and_uploaded_log():
    combined = build_user_input(
        question="请分析这段日志",
        uploaded_text="[SMF] DNN not supported",
        uploaded_filename="smf.log",
    )

    assert "请分析这段日志" in combined
    assert "上传文件：smf.log" in combined
    assert "[SMF] DNN not supported" in combined


def test_build_user_input_allows_file_only_analysis():
    combined = build_user_input(
        question="",
        uploaded_text="[UPF] PFCP Session Establishment failure",
        uploaded_filename="upf.log",
    )

    assert combined.startswith("上传文件：upf.log")
