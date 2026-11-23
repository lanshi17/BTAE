# TASK-hermes-acp-fork：ACP 会话分叉

- 类型：Feature；风险：high；实体：MOD-009；范围为 ACP 会话传输、测试、宿主文档和执行证据。
- 依据：本机 Hermes ACP `session/fork` 契约及核心生命周期记录；分叉只复制宿主会话状态，不改变 EPE 的身份、写入隔离或治理决定。
- 设计：新增 `fork_session(cwd=None)`，固定 `mcpServers: []`，校验返回的非空 child `sessionId`，并将其加入当前受控传输的允许会话集合。`prompt`、`prompt_with_updates` 和 `cancel` 可显式指定已登记的 session ID；默认仍使用父会话。未知 ID、空 ID 或已关闭会话拒绝。父子会话共用一个 JSON-RPC 读写器，普通请求仍不可并发；关闭传输同时终止全部会话。
- 验收：受控子进程验证 fork 返回 ID、父子 prompt 使用正确 ID、未知 ID 拒绝、非法返回失败关闭；真实 Hermes + 本地固定模型只创建 fork，不调用子会话模型推理。
- 限制：子会话允许集合只在本地传输句柄内维护，不是宿主授权或身份认证；不验证真实工具权限、写入隔离或跨进程恢复。设计状态 draft。

## 本轮结果

- `HermesACPSession.fork_session()` 已固定空 MCP、校验 child ID 并登记；`prompt`、`prompt_with_updates`、`cancel` 支持已登记子会话 ID，未知 ID 拒绝。
- 受控子进程覆盖父/子路由、非法返回和未知 ID；本机 Hermes 临时配置完成真实 `session/fork` 创建，未运行模型或工具。
