# 面向 5G 核心网的知识查询与故障排查 Agent

这是一个在线优先的课程大作业 Demo：Streamlit 负责 Web 页面，Python 后端使用 LangGraph 编排本地知识库、Chroma 向量检索、故障案例库、日志规则库和 OpenAI-compatible LLM API。没有 API Key 或在线调用失败时，系统会自动使用离线兜底报告。

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 在线模式配置

不要把真实 API Key 写进 `.env.example`。推荐在项目根目录新建 `.env`，内容类似：

```text
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的 API Key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=20
```

程序会自动读取 `.env`。如果同名系统环境变量已经存在，系统环境变量优先。

`.env.example` 只是模板说明；以 `#` 开头的注释行不会被读取。

## 离线兜底模式

```text
LLM_PROVIDER=offline
```

也可以不配置 `LLM_API_KEY`，系统会自动降级为离线兜底模式。

## LangGraph 与向量库

当前主流程已经升级为 LangGraph 风格工作流：

```text
Route Node
  -> Analyze Node
  -> Report Node
```

代码位置：

```text
graph/state.py      # 工作流状态
graph/workflow.py   # LangGraph 编排，缺少依赖时自动顺序兜底
agent/pipeline.py   # 调用工作流
```

知识检索使用混合检索：

```text
关键词检索：retrieval/knowledge_base.py
向量检索：retrieval/vector_store.py
持久化目录：vectorstore/chroma_db/
```

安装 `chromadb` 后会优先使用 Chroma 持久化向量库；如果当前环境还没安装 Chroma，系统会自动退回内存向量检索，Web 和测试仍可运行。

手动重建向量索引：

```powershell
python scripts/build_vector_index.py
```

输出示例：

```text
backend=chroma
documents=30
persist_dir=...\vectorstore\chroma_db
```

如果输出 `backend=memory`，说明当前 Python 环境暂时没有可用的 `chromadb`，执行 `python -m pip install -r requirements.txt` 后再重建即可。

## 模式不匹配处理

用户可以手动选择“知识查询 / 流程解释 / 故障诊断 / 日志分析”，系统也会自动识别问题类型。

当用户选择的模式和问题内容明显不匹配时，系统会自动纠偏。例如：

```text
用户选择：知识查询
用户输入：UE 注册成功但不能上网，应该怎么排查？
系统识别：故障诊断
最终采用：故障诊断
```

页面会显示“用户选择 / 系统识别 / 最终采用”，并给出纠偏提示。导出的 Markdown 报告也会保留这些信息。

## 运行 Web 页面

前台运行：

```powershell
python -m streamlit run app.py --server.port 8501
```

这个命令启动的是 Web 服务器，正常情况下会一直运行，不会返回命令提示符。浏览器访问：

```text
http://localhost:8501
```

页面输入区支持两种方式：

- 在“问题描述”中直接输入知识、流程、故障或日志问题。
- 在“上传日志/文本文件”中上传 `.log`、`.txt`、`.json`、`.yaml` 或 `.yml` 文件。

如果同时输入问题并上传文件，系统会把问题描述和文件内容合并后分析。为避免超大日志影响调用，上传内容会自动截取前 12000 个字符。

## 停止 Streamlit 服务

如果 Streamlit 是在当前终端前台运行的，按 `Ctrl+C` 即可停止。若 `Ctrl+C` 没有反应，通常说明服务是在后台进程里运行，可以用下面命令停止 8501 端口上的 Streamlit：

```powershell
$streamlitPid = (Get-NetTCPConnection -LocalPort 8501 -State Listen).OwningProcess
Stop-Process -Id $streamlitPid
```

如果想先确认进程信息：

```powershell
$streamlitPid = (Get-NetTCPConnection -LocalPort 8501 -State Listen).OwningProcess
Get-CimInstance Win32_Process -Filter "ProcessId=$streamlitPid" | Select-Object ProcessId,CommandLine
```

若想后台运行，可以使用 PowerShell：

```powershell
$out = "streamlit.out.log"
$err = "streamlit.err.log"
Start-Process -FilePath "python" `
  -ArgumentList @("-m","streamlit","run","app.py","--server.headless","true","--server.port","8501") `
  -RedirectStandardOutput $out `
  -RedirectStandardError $err `
  -WindowStyle Hidden
```

停止 8501 上的 Streamlit：

```powershell
$pid = (Get-NetTCPConnection -LocalPort 8501).OwningProcess
Stop-Process -Id $pid
```

## 已实现功能

当前版本已覆盖课程方案中的核心要求：

| 方案要求 | 当前实现 |
| --- | --- |
| Streamlit Web 界面 | `app.py`，支持问题类型选择、日志/文本文件上传、报告展示、证据区、Markdown 下载 |
| Python 后端逻辑 | `agent/pipeline.py` 串联分类、检索、分析、生成 |
| LangGraph Agent 编排 | `graph/workflow.py` 使用 LangGraph；依赖不可用时顺序兜底 |
| 向量数据库 | `retrieval/vector_store.py` 支持 Chroma，路径为 `vectorstore/chroma_db/` |
| 核心网知识查询 | `data/docs/core_network.md`，覆盖 AMF、SMF、UPF、NRF、AUSF/UDM、PCF、NSSF、关键接口 |
| 流程解释 | `data/docs/procedures.md`，覆盖 UE Registration、PDU Session、N4、Service Request、Deregistration、NRF 注册发现 |
| 故障案例库 | `data/fault_cases/fault_cases.json`，包含 15 个典型故障 |
| 日志规则库 | `data/rules/log_rules.yaml`，包含 DNN、S-NSSAI、PFCP/N4、N6、NRF、NGAP/SCTP、subscriber、DNS/endpoint 等规则 |
| 在线 LLM 模式 | `llm/llm_client.py` 支持 OpenAI-compatible API |
| 离线兜底模式 | `LLM_PROVIDER=offline` 或在线失败时自动使用模板报告 |
| 证据可解释 | 每次回答展示命中的知识片段、故障案例和日志规则 |
| 模式不匹配纠偏 | 手选类型与系统识别类型冲突时自动采用更匹配的类型并提示 |
| 预留扩展接口 | `tools/web_search.py` 和 `tools/free5gc_mcp.py` |
| 评估问题集 | `data/evaluation/test_questions.json`，包含 20 个知识、流程、故障、日志测试问题 |

当前版本仍按方案规划暂不实现：自动修改 free5GC/Open5GS 配置、自动重启网元、完整 pcap 解析、完整 3GPP 标准导入。这些适合作为报告中的“后续工作”。

## 命令行测试

```powershell
python main.py "SMF 日志中出现 DNN not supported"
python main.py "UE 注册成功但不能上网，应该怎么排查？"
python main.py "PDU Session 建立过程中 AMF、SMF、UPF 分别做什么？"
```

## 自动测试

```powershell
python -m pytest -q -p no:cacheprovider
```
