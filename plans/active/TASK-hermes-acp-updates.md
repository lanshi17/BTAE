# TASK-hermes-acp-updates：接收 ACP 会话更新

- 类型：Feature；风险：high；实体：MOD-009；写入范围：ACP 适配器、定向测试、宿主文档和本任务证据；不变更宿主授权或治理门禁。
- 问题：ACP 的模型文字通过 `session/update` 通知传输，现有 `prompt()` 跳过通知，仅返回最终响应，调用者无法获取回答。
- 设计：新增 `prompt_with_updates(text)`，返回 `(result, updates)`；updates 按收到顺序保留当前会话的 `session/update.params.update` 对象，原始字节受既有输出总上限和请求期限约束。校验 session ID 与 update 对象；无效或跨会话的更新作为协议错误并关闭会话。其他通知仍忽略，服务端请求仍不被解释为通知或授权。保留 `prompt()` 的现有返回形状和行为；不执行工具或将文字视为 EPE 决策。
- 验收：真实子进程按顺序发送文字分片，调用方可取得并与最终 stopReason 一起检查；会话不匹配及非法 update 失败关闭；无更新、输出上限、超时、取消及原有 prompt 均保持预期。
- 限制：updates 是未经信任的宿主内容；不提供身份、权限或写入隔离。设计状态 draft；真实模型及真实工具权限仍未验证。
