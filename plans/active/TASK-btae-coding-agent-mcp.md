# TASK-btae-coding-agent-mcp：Coding Agent 的 BTAE Skill 与 MCP 入口

- 类型：Feature；风险：中；影响 MOD-004 Context、MOD-007 Governance、MOD-008 CLI、MOD-009 Adapters/Agent 集成。
- 目标：让 coding agent 在设计和修改代码前获得有限、可追溯的 BTAE 上下文，并生成不具备授权效力的设计计划。
- 设计：增加 `skills/btae-coding-agent/` Skill、依赖最小的 stdio `btae` MCP server、只读 context/plan/validate tools、BTAE 章程/规格/架构/Workflow resources 和 Codex 配置示例。MCP 不写权威设计、不执行图重建、不接受自报审批、不提供宿主隔离。
- 追溯：MCP context 来源绑定仓库相对路径和 SHA-256；design plan 明确 draft、workflow 字段、实体 ID、ChangeSet、追溯链和门禁；validation 复用现有 EPE CLI 结果。
- 验收：Skill 结构校验通过；stdio initialize/tools/resources/prompts 协议回归通过；wheel 外部安装可运行 `btae-mcp`；现有全量测试无回归。
- 限制：MCP 入口是上下文和规划辅助，不替代 `epe check`、审批、CI、远程审计和宿主权限；客户端仍须把草案写入权威文档并获取适用批准。
