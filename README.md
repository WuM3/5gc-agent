# 面向 5G 核心网的知识查询与故障排查 Agent

这是一个面向 5G 核心网实验、学习和排障场景的智能 Agent。系统使用 Streamlit 提供 Web 页面，Python 负责后端逻辑，通过 LangGraph 编排问题路由、证据检索、故障分析和报告生成流程。

系统支持在线 LLM API，也支持离线兜底模式。在线模式下，LLM 会基于本地知识库、故障案例库、日志规则库和配置规则库生成结构化回答；离线模式下，系统会根据命中的本地证据生成模板化分析结果。

## 主要功能

- 知识查询：回答 5G Core 网元、接口、注册流程、PDU Session、AMF/SMF/UPF 主链路等问题。
- 故障分析：根据故障现象、日志片段或上传文件，给出涉及网元、接口、可能原因和排查步骤。
- 日志规则匹配：识别 DNN not supported、S-NSSAI mismatch、PFCP/N4 failure、N6 route/NAT、NRF discovery failed、NGAP/SCTP connection failed 等典型日志。
- 配置文件检查：上传 AMF、SMF、UPF 相关 YAML/JSON 配置文件后，检查常见缺失项，例如 AMF N2/NGAP 地址、SMF UPF/N4 拓扑、UPF N3/N6/UE 地址池等。
- 证据展示：每次回答都会展示命中的知识片段、故障案例、日志规则和配置规则，方便说明答案来源。
- 文件上传：支持上传 `.log`、`.txt`、`.json`、`.yaml`、`.yml` 文件辅助分析。
- 自动识别模式：系统会根据输入内容自动判断更适合“知识查询”还是“故障分析”。
- 报告导出：分析结果可以下载为 Markdown 报告。

## 技术栈

```text
Streamlit              Web 展示界面
Python                 后端逻辑
LangGraph              Agent 工作流编排
Chroma                 本地向量数据库
Markdown/JSON/YAML     本地知识库、案例库和规则库
OpenAI-compatible API  在线 LLM 调用
```

核心目录：

```text
app.py                         Streamlit 页面入口
main.py                        命令行入口
agent/                         路由、分析和报告生成逻辑
graph/                         LangGraph 工作流
retrieval/                     知识库、案例库和向量检索
rules/                         日志规则和配置规则检查
llm/                           LLM API 封装
data/docs/                     本地知识文档
data/fault_cases/              本地故障案例库
data/rules/                    日志规则库和配置规则库
scripts/build_vector_index.py  向量索引构建脚本
```

## 安装依赖

在项目根目录执行：

```powershell
python -m pip install -r requirements.txt
```

## 配置在线模式

在项目根目录新建 `.env` 文件，填写你的 LLM API 信息：

```text
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的 API Key
LLM_BASE_URL=https://你的接口地址/v1
LLM_MODEL=你的模型名称
LLM_TIMEOUT_SECONDS=90
```

说明：

- `.env.example` 只是模板，不要把真实 API Key 写进去。
- 如果你使用魔塔社区、智谱、DeepSeek 等 OpenAI-compatible 接口，`LLM_PROVIDER` 仍然可以保持 `openai_compatible`。
- `LLM_BASE_URL` 必须填写实际服务地址，否则可能默认请求 OpenAI 官方地址。
- 如果系统环境变量和 `.env` 同时存在，同名系统环境变量优先。

## 离线兜底模式

如果暂时不使用在线 LLM，可以在 `.env` 中设置：

```text
LLM_PROVIDER=offline
```

或者不配置 `LLM_API_KEY`，系统会自动进入离线兜底模式。离线模式仍会使用本地知识库、故障案例库、日志规则库和配置规则库生成分析结果。

## 构建向量索引

首次运行或修改 `data/docs/`、`data/fault_cases/` 后，建议重建向量索引：

```powershell
python scripts/build_vector_index.py
```

正常情况下会看到类似输出：

```text
backend=chroma
documents=39
persist_dir=...\vectorstore\chroma_db
```

如果输出 `backend=memory`，说明当前环境没有可用的 Chroma，重新安装依赖后再执行构建命令即可。

## 启动 Web 页面

前台运行：

```powershell
python -m streamlit run app.py --server.port 8501
```

浏览器访问：

```text
http://localhost:8501
```

页面使用方式：

1. 选择“自动识别”“知识查询”或“故障分析”。
2. 在问题描述中输入核心网知识、流程、故障或日志问题。
3. 如需分析日志或配置文件，点击生成按钮旁边的“上传文件”。
4. 点击生成按钮查看回答和证据区。
5. 需要保存结果时，点击“下载 Markdown 报告”。

## 停止服务

如果 Streamlit 在当前终端前台运行，按 `Ctrl+C` 停止。

如果服务在后台运行，可以查看并停止 8501 端口对应进程：

```powershell
$streamlitPid = (Get-NetTCPConnection -LocalPort 8501 -State Listen).OwningProcess
Get-CimInstance Win32_Process -Filter "ProcessId=$streamlitPid" | Select-Object ProcessId,CommandLine
Stop-Process -Id $streamlitPid
```

## 命令行使用

也可以不打开 Web 页面，直接在命令行测试：

```powershell
python main.py "什么是 5G 核心网？"
python main.py "PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？"
python main.py "SMF 日志中出现 DNN not supported"
python main.py "UE 注册成功但不能上网，应该怎么排查？"
```

## 本地数据维护

知识文档放在：

```text
data/docs/
```

故障案例放在：

```text
data/fault_cases/fault_cases.json
```

日志规则放在：

```text
data/rules/log_rules.yaml
```

配置检查规则放在：

```text
data/rules/config_rules.yaml
```

新增或修改知识文档、故障案例后，重新执行：

```powershell
python scripts/build_vector_index.py
```

## 自动测试

```powershell
python -m pytest -q -p no:cacheprovider
```
