# Agent 操作协议（本地 MVP）

`src/epe/adapters/protocol.py` 定义宿主适配器与 EPE 之间的最小请求/响应值对象。核心协议不依赖 Hermes、Codex CLI 或 Claude Code。

请求必须带 `request_id`、协议版本 1、操作（`start_implementation`、`verify`、`finalize`）、规范 `TASK-`/`CHANGE-` ID、非空目标实体、写入范围（实现操作必填且为仓库相对 glob）、64 位设计指纹和宿主注入的可信身份来源。校验拒绝绝对路径、`..`、反斜杠、空目标和错误类型。请求中的 `role: human` 或 `approved: true` 只是普通参数，不能产生授权事实。

机器契约位于 `engineering/schemas/agent-request.schema.json` 与 `agent-response.schema.json`。请求的 `protocol_version` 和 `trusted_identity.source` 是必填字段；响应的 `decision` 允许 `accepted`、`blocked`、`unsupported`、`error`，以覆盖未集成宿主的明确拒绝路径。

本地宿主适配器当前只接受 `verify`；实现和完成操作返回 `unsupported`，因为本地 CLI 没有文件写入隔离。Hermes 记录在能力矩阵中，但没有连接、身份或隔离证据前不执行任何操作。

Hermes 桥接协议使用一行 JSON 请求和一行 JSON 响应；capability handshake 的声明默认不受信，除非宿主外部配置提供可信 attestation。仓库内配置的 `trusted_capabilities` 不能替代宿主或 CI 的身份验证。

桥接器保守解析宿主响应：`operations` 必须是字符串数组；能力标志如存在，必须为 JSON 布尔值；操作响应的 `reasons`、`evidence_ids`、`next_steps` 如存在，必须是字符串数组。类型错误导致握手失败或操作返回 error，不将字符串、数字或 null 转换成可信能力或有效响应。握手声明仅为宿主自述，仍须单独验证实际权限边界。

校验失败返回 `blocked` 和稳定诊断；通过结构校验只表示请求形状可接受，后续仍须由 governance 重新检查设计、范围、证据和权限。当前协议没有把本地 CLI 变成文件系统隔离边界。

设计批准通过 `epe design approve ENTITY-ID --record PATH` 导入，不接受仅在请求中自报身份。受信签名及配置格式见[设计模块](../modules/design/README.md)；请求层的 `trusted_identity` 字段本身并不完成密码学校验或授予权限。
