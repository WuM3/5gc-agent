## 5G 核心网总体架构

5G 核心网（5G Core，简称 5GC）是 5G 系统中负责控制面管理和用户面转发的核心网络部分。它连接无线接入网、用户设备和外部数据网络，完成用户接入、鉴权、移动性管理、会话管理、策略控制、服务注册发现和数据转发等功能。

如果问“什么是核心网”，可以把它理解为移动通信系统中负责接入控制、会话控制、用户数据管理和用户面转发的核心控制与转发系统。

在架构上，5G 核心网采用服务化架构（SBA）。AMF、SMF、UPF、NRF、AUSF、UDM、PCF、NSSF 等网络功能通过标准接口协同工作。控制面主要负责注册、鉴权、会话控制和策略控制，用户面主要通过 UPF 完成 N3、N6 等数据转发。

## AMF 接入与移动性管理功能

AMF（Access and Mobility Management Function）负责 UE 注册、接入鉴权、移动性管理、NAS 信令终结和安全上下文管理。AMF 关注的是终端能否接入 5G Core，以及 UE 在接入网之间移动时如何保持控制面连接。

AMF 与 SMF 的核心区别是职责边界：AMF 管接入和移动性，SMF 管 PDU Session、地址分配、策略关联和用户面路径选择。AMF 常通过 N11 将会话相关请求转交给 SMF。

## SMF 会话管理功能

SMF（Session Management Function）负责 PDU Session 生命周期，包括会话建立、修改、释放、DNN/S-NSSAI 选择、UE IP 地址分配和 UPF 选择。SMF 通过 N11 接收 AMF 转发的会话请求，并通过 N4 控制 UPF 上的转发规则。

当排查“注册成功但无法上网”或 “DNN not supported” 时，SMF 日志通常是判断会话建立是否成功的关键位置。

## UPF 用户面功能

UPF（User Plane Function）负责用户面数据转发、QoS 执行、计费数据采集和 PDU Session Anchor。UPF 通过 N3 连接 gNB，通过 N6 连接外部数据网络，并受 SMF 通过 N4 控制。

如果 UE 已注册且 PDU Session 已建立，但仍不能访问互联网，应检查 UPF 到 DN 的 N6 路由、NAT、防火墙和数据面规则。

## NRF 服务注册与发现

NRF（Network Repository Function）负责网络功能的服务注册、发现和状态维护。AMF、SMF、AUSF、UDM 等网络功能启动后向 NRF 注册服务能力，其他网络功能再通过 NRF 查询可用服务实例。

NRF 异常会导致 AMF 找不到 AUSF/UDM，或 SMF 无法被 AMF 发现，从而引发注册、鉴权或会话建立失败。

## AUSF 与 UDM 鉴权和用户数据

AUSF（Authentication Server Function）负责 5G 鉴权流程，AMF 通常通过 N12 与 AUSF 交互，完成 UE 身份认证和鉴权向量处理。AUSF 鉴权结果会影响 UE Registration 是否能够继续。

UDM（Unified Data Management）负责统一用户数据管理，保存签约数据、鉴权相关数据、DNN/S-NSSAI 订阅信息和访问权限。AMF、SMF 等网元会通过 UDM/UDR 获取用户订阅数据；如果 UDM 中缺少 SUPI、DNN 或切片信息，就可能导致注册失败或 PDU Session 建立失败。

## PCF 策略控制功能

PCF（Policy Control Function）负责策略控制，包括会话策略、QoS 策略、计费相关策略和访问控制策略。SMF 在 PDU Session 建立或修改过程中可以向 PCF 获取会话策略，再将策略转化为 UPF 上的转发、QoS 或计费规则。

PCF 异常通常不会直接导致 UE 无法注册，但可能影响 PDU Session 策略、QoS、计费规则和用户面行为。

## NSSF 切片选择功能

NSSF（Network Slice Selection Function）负责网络切片选择，帮助 AMF 根据 UE 请求的 S-NSSAI、用户订阅和部署策略选择可用切片。NSSF 的结果会影响 AMF 后续选择 SMF 和切片相关服务。

如果 UE 请求的 S-NSSAI 与订阅或网络支持不一致，可能出现 slice not allowed、S-NSSAI mismatch 或 SMF 选择失败。

## 5G 核心网关键接口

N1 是 UE 与 AMF 之间的 NAS 控制面接口，承载注册、鉴权、会话管理等 NAS 消息。N2 是 gNB 与 AMF 之间的 NGAP 控制面接口，用于接入控制、UE 上下文和 PDU Session 资源控制。

N3 是 gNB 与 UPF 之间的用户面 GTP-U 接口，N4 是 SMF 与 UPF 之间的 PFCP 控制接口，N6 是 UPF 到外部数据网络（DN）的接口。N8 常用于 AMF 与 UDM，N10 常用于 SMF 与 UDM，N11 用于 AMF 与 SMF，N12 用于 AMF 与 AUSF，N22 可用于 AMF 与 NSSF。
