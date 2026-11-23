# Hermes ACP 取消实测记录（2026-11-23）

- Hermes：本机 `hermes-agent` v0.22.2
- 实验：临时 `HERMES_HOME` + 本地 HTTP 模型 fixture
- MCP：空列表；未启用工具
- 模型：固定本地 fixture；未访问真实模型或网络推理服务
- 状态：实验结束后临时目录清理

## 过程

1. ACP `initialize` 和 `session/new` 成功。
2. 发送纯文本 `session/prompt`，fixture 对该请求延迟响应。
3. 在 prompt 等待期间发送 ACP `session/cancel` 通知。
4. prompt 返回 `stopReason=cancelled`，JSON-RPC response ID 正确。

## 结论与限制

该结果证明 Hermes ACP 在本地 fixture 条件下支持取消通知到响应终止的链路；不证明真实模型、工具调用、宿主身份或文件写入隔离。EPE 能力矩阵继续将 `cancellation=false`，直到目标宿主和真实执行环境完成独立验收。
