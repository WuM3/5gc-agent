# 面向 5G 核心网的知识查询与故障排查 Agent 设计规格

## 目标

构建一个课程大作业级别的在线版 5G 核心网知识查询与故障排查 Agent。系统通过 Streamlit 提供 Web 展示界面，使用 Python 实现后端逻辑，结合本地知识库、故障案例库、日志规则库和统一封装的 LLM API，为用户输出结构化的知识解释或故障排查报告。

第一版聚焦可运行、可展示、可解释。在线 LLM 是系统主路径：配置 LLM API 后，报告生成必须优先通过在线模型完成。本地知识库、故障案例库和日志规则库为在线模型提供可验证证据。在未配置 API Key、用户强制选择离线模式或在线调用失败时，系统才进入离线兜底模式，仍能基于本地规则、案例和模板给出可展示结果。

## 范围

第一版实现：

- Streamlit Web 页面，支持输入问题、日志片段或故障描述。
- 自动或手动选择问题类型：知识查询、流程解释、故障诊断、日志分析。
- 本地核心网知识库，使用 markdown 文件保存 AMF、SMF、UPF、NRF、UE 注册、PDU Session 等内容。
- 本地故障案例库，第一版使用 json 保存典型 free5GC/Open5GS/UERANSIM 实验故障。
- 本地日志规则库，使用 yaml 保存关键词、涉及网元、接口、可能原因和排查步骤。
- 统一 LLM API 封装 `llm_client.py`，支持在线模式和离线兜底模式。
- 每次回答固定展示命中的知识片段、故障案例和日志规则，作为证据区。
- README 说明在线模式和离线兜底模式的切换方式。
- 在线检索接口和 free5GC-MCP 接口只预留模块和调用位置，不作为第一版必需功能。

第一版不实现：

- 自动修改 free5GC/Open5GS 配置。
- 自动重启核心网网元。
- 完整 pcap 解析。
- 完整 3GPP 标准导入和大规模向量检索。
- 生产级 LangGraph 多 Agent 编排。

## 推荐方案

采用方案 A：在线 LLM + 本地规则/RAG 的轻量 Agent。

该方案把确定性能力和生成式能力分开。本地知识库、故障案例库和日志规则库负责提供可验证证据；在线 LLM 是主要回答生成器，负责根据证据生成更自然、结构更完整的中文报告。若在线 LLM 不可用，系统使用模板化报告生成器输出离线结果。

不采用 FastAPI 前后端分离作为第一版，因为课程展示对部署简单性更敏感。也不采用完整 LangGraph 和向量数据库作为第一版核心，因为依赖和调试成本较高，容易压缩数据整理、测试和展示时间。

## 架构

代码结构：

```text
5gc-agent/
├── app.py
├── main.py
├── requirements.txt
├── README.md
├── agent/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── router.py
│   ├── analyzer.py
│   ├── report.py
│   └── schemas.py
├── retrieval/
│   ├── __init__.py
│   ├── knowledge_base.py
│   └── case_base.py
├── rules/
│   ├── __init__.py
│   └── log_rules.py
├── llm/
│   ├── __init__.py
│   └── llm_client.py
├── tools/
│   ├── __init__.py
│   ├── web_search.py
│   └── free5gc_mcp.py
├── data/
│   ├── docs/
│   ├── fault_cases/
│   └── rules/
└── tests/
    ├── test_router.py
    ├── test_rules.py
    ├── test_retrieval.py
    └── test_pipeline.py
```

各模块职责：

- `app.py`：Streamlit 页面，负责输入控件、模式显示、报告展示和证据区展示。
- `main.py`：命令行入口，方便不启动 Web 页面时快速测试 Agent。
- `agent/router.py`：根据用户输入和手动选择判断问题类型。
- `retrieval/knowledge_base.py`：读取 markdown 知识库并做轻量关键词检索。
- `retrieval/case_base.py`：读取 json 故障案例并按关键词和问题类型检索。
- `rules/log_rules.py`：读取 yaml 日志规则并匹配日志关键词。
- `agent/analyzer.py`：整合分类、知识片段、案例和规则，形成诊断上下文。
- `llm/llm_client.py`：统一封装 LLM API，默认按在线模式读取环境变量；只有配置为离线或在线调用不可用时才降级。
- `agent/report.py`：生成结构化报告。主路径优先调用在线 LLM；离线兜底模式使用模板生成。
- `tools/web_search.py`：预留在线检索接口。
- `tools/free5gc_mcp.py`：预留 free5GC-MCP 接口。

## 数据流

1. 用户在 Streamlit 输入问题、日志片段或故障描述。
2. `router.py` 判断问题类型。如果用户手动选择了类型，则优先使用手动类型。
3. `knowledge_base.py` 检索本地知识片段。
4. `case_base.py` 检索本地故障案例。
5. `log_rules.py` 匹配本地日志规则。
6. `analyzer.py` 聚合证据，提取涉及网元、接口、可能原因和建议步骤。
7. `report.py` 调用 `llm_client.py` 生成结构化报告；LLM 不可用时改用离线模板。
8. `app.py` 展示报告正文，并在证据区展示命中的知识片段、故障案例和日志规则。

## 输出格式

每次回答固定包含：

```text
问题类型：
涉及网元：
涉及接口：
诊断结论：
可能原因：
建议排查步骤：
参考依据：
运行模式：
```

证据区固定包含：

```text
命中的知识片段：
命中的故障案例：
命中的日志规则：
```

即使没有命中某一类证据，也展示空状态，例如“未命中日志规则”。这样方便课堂展示时证明系统有检索和规则支撑。

## 在线模式与离线兜底模式

`llm_client.py` 读取环境变量：

- `LLM_PROVIDER`：模型提供商，第一版支持 `openai_compatible` 和 `offline`。
- `LLM_API_KEY`：在线 API Key。
- `LLM_BASE_URL`：OpenAI-compatible API 地址。
- `LLM_MODEL`：模型名称。

切换规则：

- `LLM_PROVIDER=openai_compatible` 且 `LLM_API_KEY` 存在时使用在线模式，这是推荐和默认展示方式。
- `LLM_PROVIDER=offline` 时强制使用离线兜底模式。
- 在线调用超时、异常或缺少必要配置时，自动降级到离线兜底模式。

README 必须包含 `.env.example` 和运行命令示例，说明如何配置在线模式，以及如何不配置 API Key 直接运行离线模式。

## 错误处理

- 数据文件缺失时，页面显示明确错误，并提示缺少的文件路径。
- yaml/json 解析失败时，报告具体文件名和错误原因。
- LLM 在线调用失败时，不中断用户流程，降级到离线兜底模式，并在输出中标明运行模式。
- 检索没有命中时，仍生成基础回答，但证据区显示未命中状态。

## 测试策略

使用 pytest 覆盖核心行为：

- Router 能识别知识查询、流程解释、故障诊断、日志分析。
- 日志规则能命中 `DNN not supported`、`S-NSSAI`、`PFCP`、`N3`、`N6` 等典型关键词。
- 知识库检索能返回 AMF、SMF、UPF、NRF、PDU Session 相关片段。
- 故障案例检索能返回 DNN 不匹配、UE 注册失败、注册成功但不能上网等案例。
- Pipeline 能在无 API Key 时返回离线兜底报告，并包含证据区。
- Pipeline 能在模拟 LLM 客户端成功时返回在线模式报告。

## 展示场景

演示问题一：

```text
PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？
```

演示问题二：

```text
UE 注册成功但无法访问外网，应该怎么排查？
```

演示问题三：

```text
SMF 日志中出现 DNN not supported
```

演示重点：

- 页面能输出结构化报告。
- 报告下方能展示命中的知识片段、故障案例和日志规则。
- README 能说明在线模式和离线兜底模式切换。
- 未配置 API Key 时系统仍能稳定运行。

## 后续扩展

- 将轻量关键词检索替换为向量检索。
- 将 pipeline 升级为 LangGraph 工作流。
- 接入在线检索接口以补充新版本文档。
- 接入 free5GC-MCP 查询实验环境状态、subscriber 配置和网元运行状态。
- 增加配置文件检查和抓包字段解释工具。
