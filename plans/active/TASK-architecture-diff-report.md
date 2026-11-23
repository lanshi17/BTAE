# TASK-architecture-diff-report：预期/发现架构差异报告

- 类型：Feature；风险：中；影响 MOD-003 Graph、MOD-006 Verification、MOD-008 CLI；对应 WP-14 T6。
- 设计：新增只读 `epe architecture diff --previous-generation GENERATION`，加载当前新鲜图和调用方指定的完整历史 generation，按节点身份和完整边记录报告新增/删除及来源保真，并在同一结果中重新计算当前“预期架构”策略约束状态；历史或当前存在解析盲区时返回 `incomplete`/`blocked`。
- 边界：差异报告只描述发现架构事实，不自动判定设计违规、不修改 ADR/设计、不授予权限；ADR 协调仍需后续授权流程和人类评审。
- 验收：单元测试覆盖稳定节点/边差异、来源保留和 unknown；真实 CLI 覆盖历史 generation 选择与当前新鲜图要求。
- `expected_architecture` 只透传当前架构策略的 violations/unknowns，不自动把发现差异升级为设计违规或 ADR 决策。
