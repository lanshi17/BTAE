# TASK-changeset-conflict-coordination：ChangeSet 声明冲突查询

- 类型：Feature；风险：medium；涉及 MOD-007、MOD-008；范围为纯冲突分析、CLI、测试和文档，不实现跨进程锁。
- 问题：多个 planned/active ChangeSet 的 `write_scope` 与 `protected` 声明当前只能在各自完成时检查，Agent 无法主动发现共享文件或契约边界的协调需求。
- 设计：新增纯函数比较同一仓库的 ChangeSet 声明，识别 write/write、write/protected 和 protected/write 的潜在 glob 重叠；结果带双方 ID、owner、字段、模式和 `conservative=true`。只读取 `planned`/`active` 记录，非法记录返回诊断；不把 glob 相交当作实际写入或锁定事实。
- CLI：`epe changeset conflicts` 只读扫描配置的 ChangeSet 目录，返回 `passed`（无潜在冲突）或 `blocked`（列出所有潜在冲突）；不修改 Task、ChangeSet、审计或 Evidence。
- 验收：精确路径、通配 glob、受保护范围、无重叠和非法记录均有测试；结果稳定排序，明确误报/漏报限制。
- 限制：glob 相交采用保守候选算法，可能报告误报；不能发现动态路径、实际 Agent 身份、锁租约、跨仓库冲突或宿主强制隔离。设计状态 draft。
