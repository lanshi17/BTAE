# Hermes ACP 核心生命周期记录（2026-11-23）

- Hermes：本机 `hermes-agent` v0.22.2
- 实验脚本：Hermes 自带 `evals/acp_empty_session_wire.py` 的本地 fixture 变体
- 模型服务：本地 HTTP fixture，仅返回固定文本；未调用真实模型或网络推理服务
- 状态目录：临时 `HERMES_HOME`，实验结束后由临时目录生命周期清理
- MCP：`mcpServers: []`

## 已验证

1. ACP `initialize` 协议版本 1 握手成功。
2. `session/new` 创建会话，初始 message count 为 0。
3. `session/prompt` 发送“不要使用工具”的纯文本，返回 `stopReason=end_turn`；模型服务收到 3 个本地 fixture 请求。
4. `session/fork` 创建子会话，父子会话各保留 user/assistant 两条消息。
5. 全部 wire 交互使用 JSON-RPC，stderr 与 stdout 分离。

## 限制

该实验没有真实模型、MCP 工具、宿主身份、文件写入隔离或真实取消压力；结果证明 Hermes ACP 会话线路可运行，不证明 EPE 治理门禁或宿主权限已经建立。原始临时输出位于本机 `/tmp`，未将会话内容或凭据写入仓库。
