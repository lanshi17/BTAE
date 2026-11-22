# 工作包细化计划索引

本目录将 [总实施计划](../BTAE-implementation-plan.md) 的 14 个工作包拆成可执行明细。每份文档给出任务分解、拟议交付路径、决策项、验收映射与完成门槛；**状态反映当前执行事实：WP-01 至 WP-13 为 in_progress，WP-14 仍为 planned/not_started；**写完计划不等于实现或批准。

| WP | 里程碑 | 细化计划 | 当前状态 | 前置 |
| --- | --- | --- | --- | --- |
| WP-01 | M0 / V0.1 | [规范与机器契约冻结](WP-01-spec-freeze.md) | in_progress | 现有 PRD/SPEC/模块草案 |
| WP-02 | M1 | [工程骨架与领域模型](WP-02-core-skeleton.md) | in_progress | WP-01 |
| WP-03 | M1 | [文档与结构化工件解析](WP-03-doc-parsers.md) | in_progress | WP-02 |
| WP-04 | M1 | [Python AST 与映射检查](WP-04-ast-mapping.md) | in_progress | WP-02 |
| WP-05 | M1 | [基础图、架构规则与快照](WP-05-graph-architecture.md) | in_progress | WP-03、WP-04 |
| WP-06 | M2 | [设计校验与批准适用性](WP-06-design-approval.md) | in_progress | WP-03、WP-01 公共记录契约 |
| WP-07 | M2 | [任务、权限与质量门禁](WP-07-governance-gates.md) | in_progress | WP-06 |
| WP-08 | M2 | [检查运行器与 Evidence](WP-08-verification-evidence.md) | in_progress | WP-05、WP-07 |
| WP-09 | M2 | [统一 CLI 与应用链路](WP-09-cli-integration.md) | in_progress | WP-05 至 WP-08 |
| WP-10 | M3 | [系统验收、竞态与恢复](WP-10-system-acceptance.md) | in_progress | WP-09 |
| WP-11 | M3 | [CI、文档与 MVP 发布](WP-11-ci-release.md) | in_progress | WP-10 |
| WP-12 | M4 | [双向影响与增量图](WP-12-impact-incremental.md) | in_progress | WP-11 |
| WP-13 | M4 | [分级上下文与检索](WP-13-context-resolver.md) | in_progress | WP-12 |
| WP-14 | M5 | [宿主集成与持续演进](WP-14-host-evolution.md) | planned | WP-13 |

## 使用约定

1. 执行某 WP 前先读总计划第 7 节清单，再读本目录对应明细。
2. 明细中的路径、类名与 Schema 文件名为**拟议目标**；冻结后以 WP-01 产出为准，实现阶段不得私自改公共契约。
3. 未决决策在对应 WP 标为 **blocking** 或 **deferred**；blocking 未关闭前不得进入依赖该决策的实现。
4. 执行时创建正式 `TASK-` / `CHANGE-`，把本明细作为任务依据引用，不把本目录当作 Evidence。
5. V0.3/V1.0 的 WP-12 至 WP-14 在进入实施前可再拆子计划；当前明细用于锁定依赖与验收边界。
