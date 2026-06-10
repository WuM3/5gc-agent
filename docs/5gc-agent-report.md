# 面向 5G 核心网的知识查询与故障排查 Agent 项目报告

## 当前状态

系统主体已经完成。当前版本是在线优先的 Streamlit Web Agent，具备本地知识库、本地故障案例库、本地日志规则库、统一 LLM API 封装和离线兜底能力。

最新验证结果：

- 自动测试：`29 passed`
- Streamlit 服务：`http://localhost:8501`
- 健康检查：`200 ok`

## 启动方式

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动 Web 页面：

```powershell
python -m streamlit run app.py --server.port 8501
```

该命令是前台 Web 服务器命令，正常情况下会一直运行，不会返回命令提示符。浏览器访问：

```text
http://localhost:8501
```

命令行测试：

```powershell
python main.py "SMF 日志中出现 DNN not supported"
python main.py "UE 注册成功但不能上网，应该怎么排查？"
```

## 在线模式配置

不要把真实 API Key 写入 `.env.example`。推荐在项目根目录新建 `.env` 文件：

```text
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的 API Key
LLM_BASE_URL=你的接口地址
LLM_MODEL=你的模型名
LLM_TIMEOUT_SECONDS=20
```

程序会自动读取 `.env`。如果没有 `.env` 或没有 `LLM_API_KEY`，系统会自动进入离线兜底模式。

## 已实现功能

1. Web 展示界面

   使用 Streamlit 实现输入框、问题类型选择、运行配置展示、诊断报告展示和证据区展示。

2. 问题分类

   支持自动识别和手动选择：

   - 知识查询
   - 流程解释
   - 故障诊断
   - 日志分析

3. 本地知识库检索

   从 `data/docs/` 中检索 AMF、SMF、UPF、NRF、UE Registration、PDU Session Establishment 等知识片段。

4. 本地故障案例库检索

   从 `data/fault_cases/fault_cases.json` 中检索典型 5G 核心网实验故障，例如 DNN 不匹配、S-NSSAI 不匹配、注册成功但不能上网。

5. 日志规则匹配

   从 `data/rules/log_rules.yaml` 中匹配日志关键词，例如：

   - DNN not supported
   - S-NSSAI mismatch
   - PFCP session failure
   - N6 route or NAT

6. 在线 LLM 生成报告

   `llm/llm_client.py` 通过 OpenAI-compatible `/chat/completions` 接口调用在线模型。在线模式是主路径。

7. 离线兜底报告

   当 API Key 缺失、在线调用失败或 `LLM_PROVIDER=offline` 时，系统会根据本地证据生成结构化报告。

8. 证据区展示

   每次回答都会展示：

   - 命中的知识片段
   - 命中的故障案例
   - 命中的日志规则

   这用于证明答案来自本地检索和规则支撑，而不是单纯依赖模型生成。

## 典型演示问题

```text
PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？
```

```text
UE 注册成功但无法访问外网，应该怎么排查？
```

```text
SMF 日志中出现 DNN not supported
```

## 主要代码结构

```text
app.py                         Streamlit Web 页面
main.py                        命令行入口
config.py                      .env 配置读取
agent/router.py                问题分类
agent/analyzer.py              证据聚合
agent/report.py                报告生成与证据格式化
agent/pipeline.py              Agent 主流程
llm/llm_client.py              在线 LLM API 封装
retrieval/knowledge_base.py    本地知识库检索
retrieval/case_base.py         本地故障案例检索
rules/log_rules.py             日志规则匹配
tools/web_search.py            在线检索预留接口
tools/free5gc_mcp.py           free5GC-MCP 预留接口
```

## 后续可扩展方向

- 接入向量数据库替换轻量关键词检索。
- 接入真实在线检索接口。
- 接入 free5GC-MCP 查询实验环境状态。
- 增加配置文件检查工具。
- 增加抓包字段解释工具。
