# 本地追加式审计链

- 类型：Feature；风险：high；涉及 MOD-005、MOD-006、MOD-007、MOD-009。
- 审批导入前验证 `engineering/audit/events.jsonl`，链损坏或审计路径为符号链接时阻断；有效导入追加带 sequence、previous_hash、payload 和 hash 的事件。`epe audit verify` 检查严格字段、顺序、前置摘要和事件内容摘要。
- 这能发现工作树内的改写、删除或断链，但不是远程不可变存储；CI/宿主需保护文件权限和保留策略。
- 本地审计场景已纳入测试套件；完整测试与 CLI 证据见最近的迭代执行记录。
