# AMF SMF UPF 配置检查指南

## AMF 与 gNB 接入配置检查

AMF 与 gNB 的关键检查点是 N2/NGAP 地址、PLMN、TAI/TAC 和 S-NSSAI。gNB 必须能访问 AMF 的 NGAP/SCTP 监听地址，常见端口是 38412。UE、gNB 和 AMF 的 MCC、MNC、TAC 需要一致或处于 AMF 支持范围内，否则 UE 注册会在接入、TAI 检查或切片选择阶段失败。

如果日志出现 NGAP SCTP connection refused、SCTP reset、Registration reject、TAI not allowed，应优先核对 AMF 的 ngapIpList 或 N2 地址、gNB 中配置的 AMF 地址，以及 PLMN/TAC/S-NSSAI 是否一致。

## SMF 与 UPF 会话配置检查

SMF 与 UPF 的关键检查点是 UPF/N4 用户面拓扑、PFCP 地址、DNN 和 S-NSSAI。SMF 需要知道可用 UPF、UPF Node ID、N4/PFCP 地址和 user plane 拓扑，才能在 PDU Session 建立时选择 UPF 并下发转发规则。

如果 SMF 配置缺少 userplaneInformation、upNodes、UPF、PFCP/N4 相关字段，常见后果是 SMF 无法选择 UPF，或 N4 Session Establishment 失败。如果 DNN 或 S-NSSAI 缺失，常见后果是 DNN not supported、S-NSSAI mismatch 或 PDU Session Establishment reject。

## UPF 用户面转发配置检查

UPF 的关键检查点是 N3/GTP-U 地址、N4/PFCP 地址、UE 地址池、N6 路由和 NAT。N3/GTP-U 地址负责接收 gNB 发来的用户面隧道包，N4/PFCP 地址负责接收 SMF 下发的转发规则，N6 负责连接外部 DN。

如果 UE 能注册并建立 PDU Session，但不能 ping 外网或访问 DN，应重点检查 UPF 是否收到 N3 GTP-U 数据包、是否有对应 PDR/FAR、UE 地址池是否正确下发、N6 默认路由和返回路由是否存在，以及 NAT 或防火墙是否允许 UE 地址池出网。

## 跨文件一致性检查

free5GC、Open5GS 和 UERANSIM 常见失败并不只来自单个文件，而是来自多文件字段不一致。需要横向对比 UE、gNB、AMF、SMF、UPF 和订阅数据中的 MCC/MNC、TAC、SST/SD、DNN、AMF 地址、UPF PFCP 地址、UPF GTP-U 地址和 UE 地址池。

当前系统的配置文件规则检查以单文件提示为主，适合快速发现缺失字段。对于跨文件一致性问题，需要结合日志规则、故障案例和人工对照进一步确认。

## 规则库和 LLM 的分工

配置规则库负责确定性检查，例如“SMF 配置中没有 UPF/N4 用户面拓扑”或“UPF 配置中缺少 N3/GTP-U 地址”。LLM 不直接判断配置是否合法，而是根据命中的配置规则、日志规则、故障案例和知识片段生成解释、可能原因和排查步骤。

这种设计可以减少大模型编造，同时也承认手工规则会遗漏场景。遇到新的 free5GC/Open5GS 失败模式时，应先把日志关键词补充到日志规则库，把配置约束补充到配置规则库，再由 LLM 负责组织诊断报告。

