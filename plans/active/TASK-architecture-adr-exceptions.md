# TASK-architecture-adr-exceptions：架构规则 ADR 例外

- 类型：Feature；风险：高；影响 MOD-005 Design、MOD-006 Verification、MOD-007 Governance、MOD-008 CLI；对应 SPEC §6、WP-05/WP-07。
- 设计：架构策略支持 `exceptions` 数组，每条例外必须指定规则 ID、ADR ID、from/to 范围和 UTC `review_until`。CLI 读取注册快照，只有 `type=ADR` 且 `design_status=approved`、范围匹配且未过期的例外才传给 Architecture Validator；无效/过期/未知 ADR 产生 error，不会抑制原规则。
- 结果：Architecture report 输出实际命中的 `exceptions_applied`；已批准但范围未命中当前边的例外不会被列为已应用，原禁止依赖仍然报告。无效/过期/未知 ADR 或无效复查时间返回配置错误并保持原规则；未配置例外时保持既有行为。例外只影响对应禁止依赖，不影响循环、盲区或其他规则，也不自动改变设计/批准状态。
- 回归：真实 CLI 覆盖有效例外、范围不匹配、未批准 ADR 和无效复查时间；架构 diff 的预期报告透传已应用例外。
- 限制：当前复查期限和批准状态来自本地设计注册与策略，不能替代外部不可变评审或宿主身份；ADR 协调仍需人类授权。
