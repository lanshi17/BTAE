# TASK-ac12-closed-loop-acceptance：完整工程闭环验收

- 分类：Feature；风险：中；影响 MOD-001–MOD-009 联合；写入范围仅限验收测试、样例 fixture、计划和证据。保护现有工作。
- 依据：AC-12、WP-10 T1/T2/T4。现有测试分别覆盖任务门禁、ChangeSet、验证与配置；缺少在真实 CLI 临时工程中依次执行设计映射、模块架构、ChangeSet 范围、真实 pytest Evidence、上下文和最终任务完成的闭环证明。
- 设计：建立小型真实临时工程，包含 Module/Class Frontmatter、明确 `module_roots`、实现符号和 pytest 测试；通过子进程 CLI 初始化、任务登记、ChangeSet 建立与激活、图构建、上下文解析、测试执行、架构/映射/check 和状态完成。独立负例在验证后修改纳管源文件，确认新鲜图/证据失效并阻断完成。测试断言结构化结果、Evidence 文件和状态，不 mock 文件系统或进程执行。
- 验收：真实 CLI 完整成功场景完成 Task 与 ChangeSet；输入变化场景不能 finalize，保留真实 failed/stale 或 graph-stale 诊断；测试结果可重复。该闭环不替代 AC-01–11 的专属验收，也不代表远程 CI 强制。

- 结果：真实 subprocess CLI 成功闭环和修改输入后禁止完成两项验收通过；全量测试 176 项通过。证据见 `reports/evaluations/ac12-closed-loop.json`。WP-10 的 AC-01–11 专项覆盖、全面故障注入与 CI 仍未由本任务证明。
