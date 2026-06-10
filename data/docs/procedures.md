## UE Registration

UE Registration 用于让 UE 接入 5G Core。典型流程包括 UE 发送 Registration Request，AMF 选择 AUSF/UDM 完成鉴权和订阅数据获取，随后建立 NAS 安全上下文并返回 Registration Accept。

注册成功只能说明控制面接入完成；是否能够上网还依赖后续 PDU Session Establishment、SMF 选择、UPF 用户面路径和 N6 外部网络连通性。

## PDU Session Establishment

PDU Session 建立流程从 UE 发起 PDU Session Establishment Request 开始，AMF 通过 N11 调用 SMF 创建会话。SMF 校验 DNN、S-NSSAI 和订阅数据，选择 UPF，并在 N4 上下发用户面转发规则，最后由 AMF 将会话建立结果返回给 UE。

如果 N11 请求中的 DNN 不被订阅或切片支持，SMF 可能返回 DNN not supported，PDU Session 将无法建立。

## N4 Session Establishment

N4 Session Establishment 是 SMF 控制 UPF 建立用户面转发状态的过程。SMF 在 N4 Session Establishment Request 中下发 PDR、FAR、QER 等规则，UPF 响应后才具备处理 N3 到 N6 数据流的条件。

N4 失败会让控制面看似接近成功，但用户面规则未生效，常表现为 UE 会话建立失败或建立后无数据转发。

## Service Request

Service Request 用于 UE 从空闲态恢复业务连接，或在需要传输上行数据时重新建立与核心网的控制面和用户面资源。UE 通过 N1 发起 Service Request，gNB 通过 N2 将请求转给 AMF，AMF 恢复 UE 上下文，并根据会话状态触发 SMF 更新或恢复用户面路径。

该流程涉及 UE、gNB、AMF、SMF 和 UPF，常见排查点包括 UE 上下文是否仍有效、AMF 是否能恢复会话、N2 PDU Session Resource Setup 是否成功，以及 N3/N4 用户面资源是否正常。

## Deregistration

Deregistration 是 UE 或网络发起的注销流程，用于释放 UE 在 5G Core 中的注册状态和相关上下文。UE 可通过 N1 向 AMF 发起 Deregistration Request，AMF 清理接入和移动性上下文，并根据会话状态通知 SMF 释放 PDU Session。

排查异常注销时，应关注 AMF 日志、NAS cause、N1/N2 消息、SMF 会话释放和 UPF N4 规则删除是否一致。

## NRF Registration and Discovery

NRF Registration and Discovery 是服务化架构中的基础流程。AMF、SMF、AUSF、UDM、PCF 等网络功能启动后向 NRF 注册 NF Profile，其他网元需要调用服务时再向 NRF 查询可用实例。

如果 NRF 注册或发现失败，AMF 可能找不到 AUSF/UDM 完成鉴权，SMF 可能无法被 AMF 发现，或者 PCF/NSSF 等服务无法被调用。排查时应检查 NRF 地址、NF service name、心跳状态、OAuth/TLS 配置以及各网元注册日志。
