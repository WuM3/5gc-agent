# 5GC Agent Online Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an online-first Streamlit 5G Core knowledge query and troubleshooting Agent with local evidence retrieval and offline fallback.

**Architecture:** A Python pipeline routes the user question, retrieves local knowledge/cases/rules, sends evidence to an OpenAI-compatible LLM as the primary report generator, and falls back to a deterministic template only when online mode is unavailable. Streamlit renders the structured report and always shows matched knowledge snippets, fault cases, and log rules.

**Tech Stack:** Python 3.10+, Streamlit, requests, PyYAML, pytest, local markdown/json/yaml data files, OpenAI-compatible chat completions API.

---

## File Structure

Create these files:

- `requirements.txt`: runtime and test dependencies.
- `.env.example`: online and offline mode examples.
- `README.md`: run instructions, online-first mode, offline fallback, demo questions.
- `app.py`: Streamlit UI.
- `main.py`: CLI smoke-test entry.
- `agent/__init__.py`: package marker.
- `agent/schemas.py`: dataclasses for question type, evidence, analysis context, and report.
- `agent/router.py`: rule-based question classifier.
- `agent/analyzer.py`: evidence aggregation and diagnostic context builder.
- `agent/report.py`: online-first report generation and offline fallback template.
- `agent/pipeline.py`: end-to-end orchestration.
- `retrieval/__init__.py`: package marker.
- `retrieval/knowledge_base.py`: local markdown retrieval.
- `retrieval/case_base.py`: local JSON fault-case retrieval.
- `rules/__init__.py`: package marker.
- `rules/log_rules.py`: local YAML log-rule loading and matching.
- `llm/__init__.py`: package marker.
- `llm/llm_client.py`: OpenAI-compatible API wrapper with fallback detection.
- `tools/__init__.py`: package marker.
- `tools/web_search.py`: disabled online-search interface for future extension.
- `tools/free5gc_mcp.py`: disabled free5GC-MCP interface for future extension.
- `data/docs/core_network.md`: core NF knowledge.
- `data/docs/procedures.md`: registration and PDU Session procedures.
- `data/fault_cases/fault_cases.json`: local fault cases.
- `data/rules/log_rules.yaml`: local log keyword rules.
- `tests/test_router.py`: router tests.
- `tests/test_retrieval.py`: knowledge and case retrieval tests.
- `tests/test_rules.py`: log-rule tests.
- `tests/test_llm_client.py`: online-first and fallback LLM client tests.
- `tests/test_pipeline.py`: end-to-end pipeline tests.

The workspace is not currently a Git repository, so this plan omits commit steps. If a Git repository is initialized later, commit after each completed task.

---

### Task 1: Project Scaffold, Schemas, and Router

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `agent/__init__.py`
- Create: `agent/schemas.py`
- Create: `agent/router.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: Write the failing router tests**

Create `tests/test_router.py`:

```python
from agent.router import route_question
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
```

- [ ] **Step 2: Run the router tests to verify they fail**

Run:

```powershell
pytest tests/test_router.py -v
```

Expected: FAIL because `agent.router` does not exist.

- [ ] **Step 3: Add dependencies and schemas**

Create `requirements.txt`:

```text
streamlit>=1.35.0
requests>=2.31.0
PyYAML>=6.0.0
pytest>=8.0.0
```

Create `.env.example`:

```text
# Online-first mode, recommended for the course demo.
LLM_PROVIDER=openai_compatible
LLM_API_KEY=replace-with-your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=20

# Offline fallback mode.
# LLM_PROVIDER=offline
```

Create `agent/__init__.py` as an empty file.

Create `agent/schemas.py`:

```python
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
```

- [ ] **Step 4: Implement the router**

Create `agent/router.py`:

```python
from __future__ import annotations

from agent.schemas import QuestionType

MANUAL_TYPE_MAP = {
    QuestionType.AUTO.value: None,
    QuestionType.KNOWLEDGE.value: QuestionType.KNOWLEDGE,
    QuestionType.PROCEDURE.value: QuestionType.PROCEDURE,
    QuestionType.FAULT.value: QuestionType.FAULT,
    QuestionType.LOG.value: QuestionType.LOG,
}

LOG_KEYWORDS = ("日志", "log", "[amf]", "[smf]", "[upf]", "dnn", "not supported", "pfcp", "ngap", "sctp")
FAULT_KEYWORDS = ("失败", "异常", "不能", "无法", "排查", "故障", "ping", "不通", "注册成功但是")
PROCEDURE_KEYWORDS = ("流程", "建立", "registration", "procedure", "经过哪些", "步骤")


def route_question(question: str, manual_type: str | None = None) -> QuestionType:
    if manual_type:
        selected = MANUAL_TYPE_MAP.get(manual_type)
        if selected:
            return selected

    text = question.lower()

    if any(keyword in text for keyword in LOG_KEYWORDS):
        return QuestionType.LOG
    if any(keyword in text for keyword in FAULT_KEYWORDS):
        return QuestionType.FAULT
    if any(keyword in text for keyword in PROCEDURE_KEYWORDS):
        return QuestionType.PROCEDURE
    return QuestionType.KNOWLEDGE
```

- [ ] **Step 5: Run router tests to verify they pass**

Run:

```powershell
pytest tests/test_router.py -v
```

Expected: PASS for all 5 tests.

---

### Task 2: Local Knowledge Base and Fault Case Retrieval

**Files:**
- Create: `retrieval/__init__.py`
- Create: `retrieval/knowledge_base.py`
- Create: `retrieval/case_base.py`
- Create: `data/docs/core_network.md`
- Create: `data/docs/procedures.md`
- Create: `data/fault_cases/fault_cases.json`
- Create: `tests/test_retrieval.py`

- [ ] **Step 1: Write the failing retrieval tests**

Create `tests/test_retrieval.py`:

```python
from pathlib import Path

from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_base_finds_amf_and_smf_snippets():
    kb = KnowledgeBase(ROOT / "data" / "docs")

    hits = kb.search("AMF 和 SMF 的区别是什么？", top_k=3)

    titles = {hit.title for hit in hits}
    assert "AMF 接入与移动性管理功能" in titles
    assert "SMF 会话管理功能" in titles


def test_knowledge_base_finds_pdu_session_procedure():
    kb = KnowledgeBase(ROOT / "data" / "docs")

    hits = kb.search("PDU Session 建立流程", top_k=2)

    assert hits[0].title == "PDU Session Establishment"
    assert "N11" in hits[0].snippet


def test_fault_case_base_finds_dnn_case():
    case_base = FaultCaseBase(ROOT / "data" / "fault_cases" / "fault_cases.json")

    hits = case_base.search("SMF 日志 DNN not supported", top_k=2)

    assert hits[0].case_id == "FC-005"
    assert "SMF" in hits[0].network_functions
    assert "N11" in hits[0].interfaces


def test_fault_case_base_finds_registered_but_no_internet_case():
    case_base = FaultCaseBase(ROOT / "data" / "fault_cases" / "fault_cases.json")

    hits = case_base.search("UE 注册成功但不能上网", top_k=2)

    assert hits[0].case_id == "FC-008"
    assert "N6" in hits[0].interfaces
```

- [ ] **Step 2: Run retrieval tests to verify they fail**

Run:

```powershell
pytest tests/test_retrieval.py -v
```

Expected: FAIL because retrieval modules and data files do not exist.

- [ ] **Step 3: Add markdown knowledge data**

Create `data/docs/core_network.md`:

```markdown
# AMF 接入与移动性管理功能

AMF 负责 UE 接入控制、移动性管理、NAS 信令终结、注册管理和连接管理。AMF 主要参与 N1、N2、N11 等接口流程，在 UE Registration 中负责与 RAN、AUSF、UDM、SMF 等网元协作。

# SMF 会话管理功能

SMF 负责 PDU Session 建立、修改和释放，负责 UPF 选择、UE IP 地址分配、会话策略执行和 N4 PFCP 控制。SMF 常见接口包括 N11、N10、N7、N4。

# UPF 用户面功能

UPF 负责用户面数据转发、GTP-U 隧道处理、N3 接入侧转发、N6 数据网络连接和流量计费统计。UE 注册成功但不能上网时，应重点检查 UPF、N3、N4、N6、路由和 NAT。

# NRF 服务注册与发现

NRF 负责 5G 核心网 NF 服务注册、发现和状态管理。AMF、SMF、PCF、UDM 等网元启动后通常需要注册到 NRF，其他网元通过 NRF 发现可用服务。
```

Create `data/docs/procedures.md`:

```markdown
# UE Registration

UE Registration 包括 UE 通过 gNB 发起 NAS Registration Request，gNB 通过 N2 将消息转发给 AMF，AMF 执行鉴权、安全上下文建立、UDM 用户数据查询和注册接受。相关网元包括 UE、gNB、AMF、AUSF、UDM，相关接口包括 N1、N2、N8、N12。

# PDU Session Establishment

PDU Session Establishment 包括 UE 发起 PDU Session Establishment Request，AMF 通过 N11 请求 SMF 建立会话，SMF 查询 UDM 的订阅数据，通过 N4 控制 UPF 建立 PFCP Session，并通过 N1/N2 返回会话建立结果。相关网元包括 UE、AMF、SMF、UDM、UPF，相关接口包括 N1、N2、N11、N10、N4、N3、N6。

# N4 Session Establishment

N4 Session Establishment 是 SMF 与 UPF 之间通过 PFCP 建立用户面转发规则的过程。若 N4 失败，常见表现是 PDU Session 建立失败、UE 获取地址失败或注册成功但无法传输用户面流量。
```

- [ ] **Step 4: Add fault case JSON data**

Create `data/fault_cases/fault_cases.json`:

```json
[
  {
    "case_id": "FC-001",
    "title": "UE 注册失败：PLMN 配置错误",
    "issue_type": "故障诊断",
    "keywords": ["注册失败", "PLMN", "UERANSIM", "AMF"],
    "symptoms": ["UERANSIM UE 无法完成注册", "AMF 日志显示 PLMN 或 GUAMI 不匹配"],
    "network_functions": ["UE", "gNB", "AMF"],
    "interfaces": ["N1", "N2"],
    "possible_causes": ["UERANSIM 配置的 PLMN 与 AMF 支持的 PLMN 不一致", "AMF GUAMI 或 TAI 配置错误"],
    "next_steps": ["检查 ue.yaml 与 gnb.yaml 中的 MCC/MNC", "检查 amfcfg.yaml 中的 servedGuamiList 与 supportTaiList"],
    "evidence": "PLMN 不一致会导致 AMF 拒绝注册请求。"
  },
  {
    "case_id": "FC-005",
    "title": "PDU Session 建立失败：DNN 不匹配",
    "issue_type": "日志分析",
    "keywords": ["DNN", "not supported", "internet", "SMF", "PDU Session"],
    "symptoms": ["SMF 日志出现 DNN not supported", "UE 注册成功但 PDU Session 建立失败"],
    "network_functions": ["UE", "AMF", "SMF", "UDM", "UPF"],
    "interfaces": ["N1", "N11", "N10", "N4"],
    "possible_causes": ["subscriber 中没有配置对应 DNN", "SMF 配置中未启用该 DNN", "S-NSSAI 与 DNN 映射不一致", "UPF user-plane 未配置对应数据网络"],
    "next_steps": ["检查 WebConsole subscriber 的 DNN/S-NSSAI", "检查 smfcfg.yaml 中的 DNN 配置", "检查 upfcfg.yaml 的 user-plane 配置", "查看 SMF 与 UPF 的 PFCP Session 是否建立"],
    "evidence": "DNN not supported 通常与订阅数据、SMF DNN 支持列表或切片映射有关。"
  },
  {
    "case_id": "FC-006",
    "title": "PDU Session 建立失败：S-NSSAI 不匹配",
    "issue_type": "故障诊断",
    "keywords": ["S-NSSAI", "slice", "切片", "PDU Session", "SMF"],
    "symptoms": ["UE 请求的切片无法建立会话", "AMF 或 SMF 日志提示 slice unsupported"],
    "network_functions": ["UE", "AMF", "NSSF", "SMF", "UDM"],
    "interfaces": ["N1", "N11", "N22", "N10"],
    "possible_causes": ["UE 配置的 SST/SD 与核心网不一致", "subscriber 未配置对应 S-NSSAI", "NSSF 或 AMF 切片配置不完整"],
    "next_steps": ["检查 UE 的 configured-nssai", "检查 subscriber 的 slice 配置", "检查 AMF/NSSF/SMF 中的 S-NSSAI 支持列表"],
    "evidence": "切片不匹配会阻断 SMF 选择和 PDU Session 建立。"
  },
  {
    "case_id": "FC-008",
    "title": "UE 注册成功但不能上网",
    "issue_type": "故障诊断",
    "keywords": ["注册成功", "不能上网", "ping", "N3", "N6", "UPF", "NAT"],
    "symptoms": ["UE Registration 成功", "PDU Session 可能成功但无法 ping 外网"],
    "network_functions": ["UE", "gNB", "AMF", "SMF", "UPF", "DN"],
    "interfaces": ["N1", "N2", "N3", "N4", "N6"],
    "possible_causes": ["PDU Session 未真正建立成功", "SMF 未成功选择 UPF", "N4 PFCP Session 异常", "N3 GTP-U 隧道不通", "N6 路由或 NAT 配置错误", "UE 默认路由缺失"],
    "next_steps": ["确认 UE 是否获得 IP 地址", "检查 SMF 是否选择 UPF", "检查 N4 PFCP Session", "检查 gNB 到 UPF 的 N3 连通性", "检查 UPF 到 DN 的 N6 路由和 NAT", "检查 UE 默认路由和 DNS"],
    "evidence": "注册成功只能证明控制面接入成功，不能证明用户面 N3/N6 已经打通。"
  }
]
```

- [ ] **Step 5: Implement markdown knowledge retrieval**

Create `retrieval/__init__.py` as an empty file.

Create `retrieval/knowledge_base.py`:

```python
from __future__ import annotations

from pathlib import Path

from agent.schemas import KnowledgeHit


class KnowledgeBase:
    def __init__(self, docs_dir: Path | str) -> None:
        self.docs_dir = Path(docs_dir)
        self.sections = self._load_sections()

    def _load_sections(self) -> list[KnowledgeHit]:
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"Knowledge docs directory not found: {self.docs_dir}")

        sections: list[KnowledgeHit] = []
        for path in sorted(self.docs_dir.glob("*.md")):
            title = ""
            lines: list[str] = []
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                if raw_line.startswith("# "):
                    if title and lines:
                        sections.append(KnowledgeHit(title, str(path), "\n".join(lines).strip(), 0))
                    title = raw_line[2:].strip()
                    lines = []
                elif title:
                    lines.append(raw_line)
            if title and lines:
                sections.append(KnowledgeHit(title, str(path), "\n".join(lines).strip(), 0))
        return sections

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeHit]:
        query_terms = _tokenize(query)
        scored: list[KnowledgeHit] = []
        for section in self.sections:
            text = f"{section.title} {section.snippet}".lower()
            score = sum(1 for term in query_terms if term in text)
            if score > 0:
                scored.append(KnowledgeHit(section.title, section.source, section.snippet, score))
        return sorted(scored, key=lambda hit: (-hit.score, hit.title))[:top_k]


def _tokenize(text: str) -> set[str]:
    normalized = text.lower()
    terms = {part.strip(" ，。？！:：/[]()（）") for part in normalized.split()}
    domain_terms = {
        "amf", "smf", "upf", "nrf", "udm", "ausf", "nssf", "pcf",
        "pdu", "session", "registration", "n1", "n2", "n3", "n4", "n6", "n10", "n11",
        "注册", "流程", "建立", "上网", "会话", "用户面", "控制面",
    }
    terms.update(term for term in domain_terms if term in normalized)
    return {term for term in terms if term}
```

- [ ] **Step 6: Implement JSON fault case retrieval**

Create `retrieval/case_base.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.schemas import FaultCaseHit


class FaultCaseBase:
    def __init__(self, cases_path: Path | str) -> None:
        self.cases_path = Path(cases_path)
        self.cases = self._load_cases()

    def _load_cases(self) -> list[dict[str, Any]]:
        if not self.cases_path.exists():
            raise FileNotFoundError(f"Fault case file not found: {self.cases_path}")
        return json.loads(self.cases_path.read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = 3) -> list[FaultCaseHit]:
        query_terms = _tokenize(query)
        hits: list[FaultCaseHit] = []
        for item in self.cases:
            searchable = " ".join(
                [
                    item["title"],
                    item["issue_type"],
                    " ".join(item.get("keywords", [])),
                    " ".join(item.get("symptoms", [])),
                    " ".join(item.get("possible_causes", [])),
                    " ".join(item.get("next_steps", [])),
                ]
            ).lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                hits.append(
                    FaultCaseHit(
                        case_id=item["case_id"],
                        title=item["title"],
                        issue_type=item["issue_type"],
                        symptoms=item["symptoms"],
                        network_functions=item["network_functions"],
                        interfaces=item["interfaces"],
                        possible_causes=item["possible_causes"],
                        next_steps=item["next_steps"],
                        evidence=item["evidence"],
                        score=score,
                    )
                )
        return sorted(hits, key=lambda hit: (-hit.score, hit.case_id))[:top_k]


def _tokenize(text: str) -> set[str]:
    normalized = text.lower()
    terms = {part.strip(" ，。？！:：/[]()（）") for part in normalized.split()}
    domain_terms = {
        "dnn", "s-nssai", "snssai", "pfcp", "pdu", "session", "smf", "amf", "upf",
        "n3", "n4", "n6", "n10", "n11", "注册", "成功", "不能", "上网", "失败", "切片",
    }
    terms.update(term for term in domain_terms if term in normalized)
    return {term for term in terms if term}
```

- [ ] **Step 7: Run retrieval tests to verify they pass**

Run:

```powershell
pytest tests/test_retrieval.py -v
```

Expected: PASS for all 4 tests.

---

### Task 3: Log Rules and Evidence Analyzer

**Files:**
- Create: `rules/__init__.py`
- Create: `rules/log_rules.py`
- Create: `agent/analyzer.py`
- Create: `data/rules/log_rules.yaml`
- Create: `tests/test_rules.py`

- [ ] **Step 1: Write the failing log-rule tests**

Create `tests/test_rules.py`:

```python
from pathlib import Path

from agent.analyzer import Analyzer
from agent.schemas import QuestionType
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


ROOT = Path(__file__).resolve().parents[1]


def test_log_rules_match_dnn_not_supported():
    rules = LogRuleBase(ROOT / "data" / "rules" / "log_rules.yaml")

    hits = rules.match("[SMF] DNN internet is not supported")

    assert hits[0].keyword == "DNN not supported"
    assert hits[0].nf == "SMF"
    assert "N11" in hits[0].interface


def test_log_rules_match_n6_route_or_nat_problem():
    rules = LogRuleBase(ROOT / "data" / "rules" / "log_rules.yaml")

    hits = rules.match("UE can register but cannot ping internet, maybe NAT error on N6")

    assert hits[0].keyword == "N6 route or NAT"
    assert hits[0].nf == "UPF"


def test_analyzer_merges_evidence_into_context():
    analyzer = Analyzer(
        knowledge_base=KnowledgeBase(ROOT / "data" / "docs"),
        case_base=FaultCaseBase(ROOT / "data" / "fault_cases" / "fault_cases.json"),
        rule_base=LogRuleBase(ROOT / "data" / "rules" / "log_rules.yaml"),
    )

    context = analyzer.analyze("SMF 日志 DNN not supported", QuestionType.LOG)

    assert "SMF" in context.network_functions
    assert "N11" in context.interfaces
    assert any("subscriber" in cause for cause in context.possible_causes)
    assert context.knowledge_hits
    assert context.case_hits
    assert context.rule_hits
```

- [ ] **Step 2: Run log-rule tests to verify they fail**

Run:

```powershell
pytest tests/test_rules.py -v
```

Expected: FAIL because `rules.log_rules` and `agent.analyzer` do not exist.

- [ ] **Step 3: Add log rule YAML data**

Create `data/rules/log_rules.yaml`:

```yaml
- keyword: "DNN not supported"
  patterns:
    - "DNN not supported"
    - "not supported"
  nf: "SMF"
  interface: "N11/N10/N4"
  severity: "high"
  possible_causes:
    - "subscriber 中没有配置对应 DNN"
    - "SMF 配置中未启用该 DNN"
    - "S-NSSAI 与 DNN 映射错误"
    - "UPF user-plane 缺少对应数据网络配置"
  next_steps:
    - "检查 WebConsole subscriber 的 DNN/S-NSSAI 配置"
    - "检查 smfcfg.yaml 中的 DNN 支持列表"
    - "检查 UPF user-plane 和数据网络配置"
    - "查看 SMF 与 UPF 的 PFCP Session 是否建立成功"
- keyword: "S-NSSAI mismatch"
  patterns:
    - "S-NSSAI"
    - "slice unsupported"
    - "snssai"
  nf: "AMF/SMF/NSSF"
  interface: "N1/N11/N22/N10"
  severity: "medium"
  possible_causes:
    - "UE 请求的 SST/SD 与核心网配置不一致"
    - "subscriber 缺少对应 S-NSSAI"
    - "NSSF、AMF 或 SMF 切片支持列表不一致"
  next_steps:
    - "检查 UE configured-nssai"
    - "检查 subscriber slice 配置"
    - "检查 AMF、NSSF、SMF 的 S-NSSAI 支持列表"
- keyword: "PFCP session failure"
  patterns:
    - "PFCP"
    - "N4"
    - "session establishment failed"
  nf: "SMF/UPF"
  interface: "N4"
  severity: "high"
  possible_causes:
    - "SMF 无法连接 UPF"
    - "UPF 地址或端口配置错误"
    - "防火墙阻断 PFCP UDP 8805"
  next_steps:
    - "检查 smfcfg.yaml 中 UPF 地址"
    - "检查 UPF 是否监听 PFCP 端口"
    - "检查 SMF 到 UPF 的 UDP 8805 连通性"
- keyword: "N6 route or NAT"
  patterns:
    - "N6"
    - "NAT"
    - "cannot ping"
    - "不能上网"
  nf: "UPF"
  interface: "N6"
  severity: "medium"
  possible_causes:
    - "UPF 到 DN 的路由缺失"
    - "NAT 转换未配置"
    - "UE 默认路由或 DNS 配置异常"
  next_steps:
    - "检查 UPF 主机路由表"
    - "检查 NAT 或 masquerade 规则"
    - "确认 UE IP 地址、默认路由和 DNS"
```

- [ ] **Step 4: Implement log rule matching**

Create `rules/__init__.py` as an empty file.

Create `rules/log_rules.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent.schemas import LogRuleHit


class LogRuleBase:
    def __init__(self, rules_path: Path | str) -> None:
        self.rules_path = Path(rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict[str, Any]]:
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Log rule file not found: {self.rules_path}")
        loaded = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
        return loaded or []

    def match(self, text: str, top_k: int = 3) -> list[LogRuleHit]:
        normalized = text.lower()
        hits: list[LogRuleHit] = []
        for item in self.rules:
            score = sum(1 for pattern in item.get("patterns", []) if pattern.lower() in normalized)
            if score > 0:
                hits.append(
                    LogRuleHit(
                        keyword=item["keyword"],
                        nf=item["nf"],
                        interface=item["interface"],
                        possible_causes=item["possible_causes"],
                        next_steps=item["next_steps"],
                        severity=item["severity"],
                        score=score,
                    )
                )
        return sorted(hits, key=lambda hit: (-hit.score, hit.keyword))[:top_k]
```

- [ ] **Step 5: Implement the evidence analyzer**

Create `agent/analyzer.py`:

```python
from __future__ import annotations

from agent.schemas import AnalysisContext, QuestionType
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


class Analyzer:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        case_base: FaultCaseBase,
        rule_base: LogRuleBase,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.case_base = case_base
        self.rule_base = rule_base

    def analyze(self, question: str, question_type: QuestionType) -> AnalysisContext:
        knowledge_hits = self.knowledge_base.search(question, top_k=3)
        case_hits = self.case_base.search(question, top_k=3)
        rule_hits = self.rule_base.match(question, top_k=3)

        network_functions = _unique(
            [nf for hit in case_hits for nf in hit.network_functions]
            + [part for hit in rule_hits for part in hit.nf.replace("/", ",").split(",")]
        )
        interfaces = _unique(
            [interface for hit in case_hits for interface in hit.interfaces]
            + [part for hit in rule_hits for part in hit.interface.replace("/", ",").split(",")]
        )
        possible_causes = _unique(
            [cause for hit in case_hits for cause in hit.possible_causes]
            + [cause for hit in rule_hits for cause in hit.possible_causes]
        )
        next_steps = _unique(
            [step for hit in case_hits for step in hit.next_steps]
            + [step for hit in rule_hits for step in hit.next_steps]
        )

        return AnalysisContext(
            question=question,
            question_type=question_type,
            knowledge_hits=knowledge_hits,
            case_hits=case_hits,
            rule_hits=rule_hits,
            network_functions=network_functions,
            interfaces=interfaces,
            possible_causes=possible_causes,
            next_steps=next_steps,
        )


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
```

- [ ] **Step 6: Run log-rule tests to verify they pass**

Run:

```powershell
pytest tests/test_rules.py -v
```

Expected: PASS for all 3 tests.

---

### Task 4: Online-First LLM Client

**Files:**
- Create: `llm/__init__.py`
- Create: `llm/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write the failing LLM client tests**

Create `tests/test_llm_client.py`:

```python
from llm.llm_client import LLMClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_llm_client_uses_online_mode_when_api_key_exists(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "demo-model")

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse({"choices": [{"message": {"content": "在线报告"}}]})

    client = LLMClient(post=fake_post)

    result = client.generate("请生成报告")

    assert result.mode == "online"
    assert result.content == "在线报告"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "demo-model"


def test_llm_client_falls_back_when_api_key_is_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    client = LLMClient(post=lambda **kwargs: None)

    result = client.generate("请生成报告")

    assert result.mode == "offline"
    assert "LLM_API_KEY" in result.error


def test_llm_client_falls_back_when_provider_is_offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")

    client = LLMClient(post=lambda **kwargs: None)

    result = client.generate("请生成报告")

    assert result.mode == "offline"
    assert "offline" in result.error


def test_llm_client_falls_back_when_http_call_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def failing_post(url, headers, json, timeout):
        raise RuntimeError("network down")

    client = LLMClient(post=failing_post)

    result = client.generate("请生成报告")

    assert result.mode == "offline"
    assert "network down" in result.error
```

- [ ] **Step 2: Run LLM client tests to verify they fail**

Run:

```powershell
pytest tests/test_llm_client.py -v
```

Expected: FAIL because `llm.llm_client` does not exist.

- [ ] **Step 3: Implement online-first LLM client**

Create `llm/__init__.py` as an empty file.

Create `llm/llm_client.py`:

```python
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import requests

from agent.schemas import LLMResult


class LLMClient:
    def __init__(self, post: Callable[..., Any] | None = None) -> None:
        self._post = post or requests.post

    def generate(self, prompt: str) -> LLMResult:
        provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
        if provider == "offline":
            return LLMResult(content="", mode="offline", error="LLM_PROVIDER is offline")
        if provider != "openai_compatible":
            return LLMResult(content="", mode="offline", error=f"Unsupported LLM_PROVIDER: {provider}")

        api_key = os.getenv("LLM_API_KEY", "").strip()
        if not api_key:
            return LLMResult(content="", mode="offline", error="LLM_API_KEY is not configured")

        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

        try:
            response = self._post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是面向 5G 核心网实验环境的知识查询与故障排查 Agent。必须基于给定证据回答，不要编造未给出的配置状态。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return LLMResult(content=content, mode="online")
        except Exception as exc:
            return LLMResult(content="", mode="offline", error=str(exc))
```

- [ ] **Step 4: Run LLM client tests to verify they pass**

Run:

```powershell
pytest tests/test_llm_client.py -v
```

Expected: PASS for all 4 tests.

---

### Task 5: Report Generator and End-to-End Pipeline

**Files:**
- Create: `agent/report.py`
- Create: `agent/pipeline.py`
- Create: `main.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Create `tests/test_pipeline.py`:

```python
from pathlib import Path

from agent.pipeline import AgentPipeline
from agent.schemas import LLMResult


ROOT = Path(__file__).resolve().parents[1]


class FakeOnlineLLM:
    def generate(self, prompt: str) -> LLMResult:
        assert "命中的知识片段" in prompt
        assert "命中的故障案例" in prompt
        assert "命中的日志规则" in prompt
        return LLMResult(content="在线结构化报告", mode="online")


class FakeOfflineLLM:
    def generate(self, prompt: str) -> LLMResult:
        return LLMResult(content="", mode="offline", error="missing key")


def test_pipeline_prefers_online_llm_report():
    pipeline = AgentPipeline(root_dir=ROOT, llm_client=FakeOnlineLLM())

    report = pipeline.run("SMF 日志中出现 DNN not supported")

    assert report.mode == "online"
    assert report.content == "在线结构化报告"
    assert report.context.knowledge_hits
    assert report.context.case_hits
    assert report.context.rule_hits


def test_pipeline_offline_fallback_still_contains_structured_sections():
    pipeline = AgentPipeline(root_dir=ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("UE 注册成功但不能上网")

    assert report.mode == "offline"
    assert "问题类型：" in report.content
    assert "涉及网元：" in report.content
    assert "建议排查步骤：" in report.content
    assert report.context.case_hits


def test_pipeline_manual_type_overrides_router():
    pipeline = AgentPipeline(root_dir=ROOT, llm_client=FakeOfflineLLM())

    report = pipeline.run("AMF 的作用是什么？", manual_type="故障诊断")

    assert report.context.question_type.value == "故障诊断"
```

- [ ] **Step 2: Run pipeline tests to verify they fail**

Run:

```powershell
pytest tests/test_pipeline.py -v
```

Expected: FAIL because `agent.pipeline` and `agent.report` do not exist.

- [ ] **Step 3: Implement report generation**

Create `agent/report.py`:

```python
from __future__ import annotations

from agent.schemas import AgentReport, AnalysisContext
from llm.llm_client import LLMClient


class ReportGenerator:
    def __init__(self, llm_client: object | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def generate(self, context: AnalysisContext) -> AgentReport:
        prompt = build_prompt(context)
        result = self.llm_client.generate(prompt)
        if result.mode == "online" and result.content.strip():
            return AgentReport(content=result.content.strip(), mode="online", context=context)

        return AgentReport(
            content=build_offline_report(context, result.error),
            mode="offline",
            context=context,
            llm_error=result.error,
        )


def build_prompt(context: AnalysisContext) -> str:
    return f"""请基于下面证据生成中文结构化报告。

要求：
1. 必须包含：问题类型、涉及网元、涉及接口、诊断结论、可能原因、建议排查步骤、参考依据、运行模式。
2. 运行模式写“在线模式”。
3. 不要编造证据区没有提供的配置状态。

用户问题：
{context.question}

问题类型：
{context.question_type.value}

命中的知识片段：
{format_knowledge_hits(context)}

命中的故障案例：
{format_case_hits(context)}

命中的日志规则：
{format_rule_hits(context)}
"""


def build_offline_report(context: AnalysisContext, error: str | None = None) -> str:
    return "\n".join(
        [
            f"问题类型：{context.question_type.value}",
            f"涉及网元：{_join_or_empty(context.network_functions)}",
            f"涉及接口：{_join_or_empty(context.interfaces)}",
            "诊断结论：系统未能调用在线 LLM，已根据本地知识库、故障案例库和日志规则库生成兜底诊断。",
            "可能原因：",
            _numbered(context.possible_causes),
            "建议排查步骤：",
            _numbered(context.next_steps),
            "参考依据：本地知识片段、故障案例和日志规则。",
            "运行模式：离线兜底模式",
            f"降级原因：{error or '未提供在线模型输出'}",
        ]
    )


def format_knowledge_hits(context: AnalysisContext) -> str:
    if not context.knowledge_hits:
        return "未命中知识片段"
    return "\n".join(f"- {hit.title}（{hit.source}）：{hit.snippet}" for hit in context.knowledge_hits)


def format_case_hits(context: AnalysisContext) -> str:
    if not context.case_hits:
        return "未命中故障案例"
    return "\n".join(f"- {hit.case_id} {hit.title}：{hit.evidence}" for hit in context.case_hits)


def format_rule_hits(context: AnalysisContext) -> str:
    if not context.rule_hits:
        return "未命中日志规则"
    return "\n".join(f"- {hit.keyword}：{hit.nf}，{hit.interface}，严重度 {hit.severity}" for hit in context.rule_hits)


def _join_or_empty(values: list[str]) -> str:
    return "、".join(values) if values else "未从本地证据中识别"


def _numbered(values: list[str]) -> str:
    if not values:
        return "1. 未从本地证据中识别明确原因"
    return "\n".join(f"{index}. {value}" for index, value in enumerate(values, start=1))
```

- [ ] **Step 4: Implement the pipeline**

Create `agent/pipeline.py`:

```python
from __future__ import annotations

from pathlib import Path

from agent.analyzer import Analyzer
from agent.report import ReportGenerator
from agent.router import route_question
from agent.schemas import AgentReport
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


class AgentPipeline:
    def __init__(self, root_dir: Path | str | None = None, llm_client: object | None = None) -> None:
        self.root_dir = Path(root_dir or Path(__file__).resolve().parents[1])
        self.analyzer = Analyzer(
            knowledge_base=KnowledgeBase(self.root_dir / "data" / "docs"),
            case_base=FaultCaseBase(self.root_dir / "data" / "fault_cases" / "fault_cases.json"),
            rule_base=LogRuleBase(self.root_dir / "data" / "rules" / "log_rules.yaml"),
        )
        self.report_generator = ReportGenerator(llm_client=llm_client)

    def run(self, question: str, manual_type: str | None = None) -> AgentReport:
        question_type = route_question(question, manual_type=manual_type)
        context = self.analyzer.analyze(question, question_type)
        return self.report_generator.generate(context)
```

- [ ] **Step 5: Add CLI entry**

Create `main.py`:

```python
from __future__ import annotations

import argparse

from agent.pipeline import AgentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="5G Core knowledge query and troubleshooting Agent")
    parser.add_argument("question", help="核心网问题、日志片段或故障描述")
    parser.add_argument("--type", dest="manual_type", default=None, help="手动问题类型：知识查询/流程解释/故障诊断/日志分析")
    args = parser.parse_args()

    report = AgentPipeline().run(args.question, manual_type=args.manual_type)
    print(report.content)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run pipeline tests to verify they pass**

Run:

```powershell
pytest tests/test_pipeline.py -v
```

Expected: PASS for all 3 tests.

---

### Task 6: Streamlit UI and Reserved Tool Interfaces

**Files:**
- Create: `app.py`
- Create: `tools/__init__.py`
- Create: `tools/web_search.py`
- Create: `tools/free5gc_mcp.py`

- [ ] **Step 1: Create reserved tool modules**

Create `tools/__init__.py` as an empty file.

Create `tools/web_search.py`:

```python
from __future__ import annotations


def search_web(query: str) -> dict[str, object]:
    return {
        "enabled": False,
        "query": query,
        "message": "在线检索接口已预留，第一版未启用。",
        "results": [],
    }
```

Create `tools/free5gc_mcp.py`:

```python
from __future__ import annotations


def query_free5gc_mcp(command: str) -> dict[str, object]:
    return {
        "enabled": False,
        "command": command,
        "message": "free5GC-MCP 接口已预留，第一版未启用。",
        "result": None,
    }
```

- [ ] **Step 2: Create Streamlit UI**

Create `app.py`:

```python
from __future__ import annotations

import os

import streamlit as st

from agent.pipeline import AgentPipeline
from agent.report import format_case_hits, format_knowledge_hits, format_rule_hits
from agent.schemas import QuestionType


st.set_page_config(page_title="5G Core Agent", page_icon="5GC", layout="wide")

st.title("面向 5G 核心网的知识查询与故障排查 Agent")

with st.sidebar:
    st.subheader("运行配置")
    provider = os.getenv("LLM_PROVIDER", "openai_compatible")
    has_key = bool(os.getenv("LLM_API_KEY", "").strip())
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    st.write(f"LLM Provider：`{provider}`")
    st.write(f"LLM Model：`{model}`")
    st.write("API Key：已配置" if has_key else "API Key：未配置")
    st.caption("在线模式是主路径；缺少 Key 或调用失败时自动进入离线兜底模式。")

question_type = st.selectbox(
    "问题类型",
    [item.value for item in QuestionType],
    index=0,
)

question = st.text_area(
    "输入核心网问题、日志片段或故障描述",
    value="SMF 日志中出现 DNN not supported",
    height=160,
)

run = st.button("生成诊断报告", type="primary")

if run:
    if not question.strip():
        st.warning("请输入问题、日志片段或故障描述。")
    else:
        with st.spinner("正在检索本地证据并调用在线 LLM..."):
            report = AgentPipeline().run(question.strip(), manual_type=question_type)

        mode_label = "在线模式" if report.mode == "online" else "离线兜底模式"
        st.success(f"报告生成完成：{mode_label}")
        if report.llm_error:
            st.info(f"在线调用降级原因：{report.llm_error}")

        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("诊断报告")
            st.markdown(report.content)

        with right:
            st.subheader("证据区")
            with st.expander("命中的知识片段", expanded=True):
                st.markdown(format_knowledge_hits(report.context))
            with st.expander("命中的故障案例", expanded=True):
                st.markdown(format_case_hits(report.context))
            with st.expander("命中的日志规则", expanded=True):
                st.markdown(format_rule_hits(report.context))
```

- [ ] **Step 3: Manually smoke-test the CLI fallback path**

Run:

```powershell
$env:LLM_PROVIDER='offline'
python main.py "SMF 日志中出现 DNN not supported"
```

Expected: output contains `运行模式：离线兜底模式`, `DNN`, and `SMF`.

- [ ] **Step 4: Start the Streamlit app**

Run:

```powershell
streamlit run app.py
```

Expected: local URL appears, usually `http://localhost:8501`, and the page shows input controls, run configuration, report, and evidence expanders.

---

### Task 7: README, Final Verification, and Demo Questions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# 面向 5G 核心网的知识查询与故障排查 Agent

这是一个课程大作业项目：使用 Streamlit、Python、本地知识库、故障案例库、日志规则库和在线 LLM API，构建面向 free5GC/Open5GS/UERANSIM 实验场景的 5G 核心网知识查询与故障排查 Agent。

## 功能

- 核心网知识查询：AMF、SMF、UPF、NRF 等网元说明。
- 流程解释：UE Registration、PDU Session Establishment、N4 Session Establishment。
- 故障诊断：UE 注册失败、PDU Session 建立失败、注册成功但不能上网。
- 日志分析：DNN not supported、S-NSSAI mismatch、PFCP/N4、N6 route/NAT。
- 证据展示：每次回答都展示命中的知识片段、故障案例和日志规则。
- 在线优先：优先调用 OpenAI-compatible LLM API 生成报告。
- 离线兜底：缺少 API Key 或在线调用失败时，自动使用本地模板生成报告。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 在线模式，推荐

在线模式是本项目主要展示方式。复制 `.env.example` 中的配置到你的系统环境变量，或在 PowerShell 中设置：

```powershell
$env:LLM_PROVIDER='openai_compatible'
$env:LLM_API_KEY='你的 API Key'
$env:LLM_BASE_URL='https://api.openai.com/v1'
$env:LLM_MODEL='gpt-4o-mini'
$env:LLM_TIMEOUT_SECONDS='20'
```

只要 `LLM_PROVIDER=openai_compatible` 且 `LLM_API_KEY` 存在，系统就会优先调用在线 LLM。

## 离线兜底模式

离线模式用于没有 API Key、网络异常或课堂演示保底：

```powershell
$env:LLM_PROVIDER='offline'
```

也可以不设置 `LLM_API_KEY`，系统会自动降级为离线兜底模式。离线模式仍会检索本地知识库、故障案例库和日志规则库，并输出结构化报告。

## 运行 Web 页面

```powershell
streamlit run app.py
```

打开终端显示的本地地址，通常是：

```text
http://localhost:8501
```

## 命令行测试

```powershell
python main.py "SMF 日志中出现 DNN not supported"
python main.py "UE 注册成功但不能上网，应该怎么排查？"
python main.py "PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？"
```

## 测试

```powershell
pytest -v
```

## Demo 问题

1. `PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？`
2. `UE 注册成功但无法访问外网，应该怎么排查？`
3. `SMF 日志中出现 DNN not supported`

## 数据目录

- `data/docs/`：本地核心网知识库，markdown 文件。
- `data/fault_cases/fault_cases.json`：本地故障案例库。
- `data/rules/log_rules.yaml`：本地日志规则库。

## 扩展接口

- `tools/web_search.py`：在线检索接口预留。
- `tools/free5gc_mcp.py`：free5GC-MCP 接口预留。
```

- [ ] **Step 2: Run the complete automated test suite**

Run:

```powershell
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Run CLI online-mode smoke test with fake or real environment**

If an API key is available, run:

```powershell
$env:LLM_PROVIDER='openai_compatible'
$env:LLM_API_KEY='你的 API Key'
$env:LLM_BASE_URL='https://api.openai.com/v1'
$env:LLM_MODEL='gpt-4o-mini'
python main.py "SMF 日志中出现 DNN not supported"
```

Expected: output is an online model report and includes structured 5G core troubleshooting content.

- [ ] **Step 4: Run CLI fallback smoke test**

Run:

```powershell
$env:LLM_PROVIDER='offline'
python main.py "UE 注册成功但不能上网"
```

Expected: output includes `运行模式：离线兜底模式`, `UPF`, `N3`, and `N6`.

- [ ] **Step 5: Run Streamlit smoke test**

Run:

```powershell
streamlit run app.py
```

Expected: Streamlit starts, the page accepts the three demo questions, and the evidence section always shows knowledge snippets, fault cases, and log rules or clear empty-state text.

---

## Self-Review

- Spec coverage: Tasks cover Streamlit UI, Python pipeline, local markdown/json/yaml data, online-first LLM wrapper, offline fallback, evidence display, README mode switching, reserved online search, reserved free5GC-MCP, and tests.
- Scope: The plan does not include automatic config mutation, service restart, full pcap parsing, large 3GPP ingestion, or production LangGraph orchestration.
- Type consistency: `QuestionType`, `KnowledgeHit`, `FaultCaseHit`, `LogRuleHit`, `AnalysisContext`, `LLMResult`, and `AgentReport` are defined in Task 1 and reused consistently.
- Online priority: Task 4 and Task 5 make online generation the primary path; offline is only used when explicitly selected or when online mode cannot produce content.
