# AMF SMF UPF 主链路

## UE 到 DN 用户面路径

UE 到 DN 的上下行路径可以按控制面和用户面分开理解。控制面负责注册、鉴权、会话建立和策略选择，核心网元主要是 AMF、SMF、UDM、AUSF、PCF、NRF。用户面负责真实业务数据转发，主路径是 UE -> gNB -> UPF -> DN。

下行方向通常是 DN 将数据发往 UPF 的 N6 侧接口，UPF 根据 PDR/FAR 等转发规则封装为 GTP-U，经 N3 发往 gNB，最后由 gNB 发给 UE。上行方向是 UE 业务包到达 gNB 后，经 N3 GTP-U 隧道进入 UPF，UPF 解封装后从 N6 转发到 DN。排查“能注册但不能上网”时，应同时检查 N3 GTP-U、UPF N6 路由、UE 地址池和 NAT/防火墙。

## PDU Session 建立中的 AMF SMF UPF

PDU Session 建立时，UE 通过 NAS 消息向 AMF 发起会话请求，AMF 根据 DNN、S-NSSAI、NSSAI、SUPI 和本地或 NRF/NSSF 选择结果找到合适的 SMF。SMF 负责会话管理、UE 地址分配、策略执行和 UPF 选择，并通过 N4/PFCP 向 UPF 下发 PDR、FAR、QER 等转发规则。

如果 SMF 找不到 UPF，常见表现是 N4/PFCP association failed、PFCP Session Establishment failure 或 PDU Session Establishment reject。如果 DNN 或 S-NSSAI 不匹配，常见表现是 DNN not supported、slice not allowed、S-NSSAI mismatch。

## N2 N3 N4 N6 接口关系

N2 是 gNB 和 AMF 之间的控制面接口，承载 NGAP，底层常见为 SCTP。N3 是 gNB 和 UPF 之间的用户面接口，承载 GTP-U。N4 是 SMF 和 UPF 之间的控制接口，承载 PFCP，用于建立和更新用户面转发规则。N6 是 UPF 和外部 DN 之间的接口，涉及数据网络路由、NAT 和防火墙。

这几个接口的排查顺序通常是先确认 N2 注册正常，再确认 N11/SMF 会话选择正常，再看 N4/PFCP 是否成功，最后检查 N3/N6 是否有业务包和返回路由。

## 主链路常见观测点

AMF 侧重点看 UE Registration、NGAP Initial UE Message、Authentication、Security Mode、Registration Accept，以及 gNB SCTP 连接状态。SMF 侧重点看 PDU Session Establishment、DNN/S-NSSAI、UE IP 分配、UPF selection、PFCP association。UPF 侧重点看 PFCP association、N4 session、N3 GTP-U 收包、N6 出口路由和 NAT。

