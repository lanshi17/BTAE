# TASK-module-status-synchronization：模块状态与本地证据同步

- 分类：Refactor / Governance；风险：中；影响 MOD-001–MOD-009 模块设计文档、模块索引和证据索引；不改变运行时行为。
- 根因：9 个模块已有本地实现、CLI/集成测试和 192 项全量回归，但各模块 frontmatter 仍统一为 `in_progress/pending`，与当前可验证状态不一致；同时部分 V1.0/外部能力明确 deferred。
- 设计：将模块实现状态同步为 `implemented`，验证状态同步为 `passed`，含义限定为本仓库本地基线范围；保留各模块文档中的 deferred 限制（Hermes 真实宿主、远程不可变审计、多语言/向量后端、平台扩展）。设计状态仍为 draft，未伪造审批。新增机器可读状态审计，列出每个模块的本地证据、支持范围和 deferred 项。
- 验收：状态文件与 frontmatter 一致；模块索引仍明确“本地基线”和外部 deferred；全量测试和 `git diff --check` 通过。整体目标不因本地状态同步而宣称所有外部能力完成。

- 结果：9 个模块文档已同步为本地基线 `implemented/passed`，设计状态仍为 draft；状态审计列出每个模块的本地范围和 deferred 能力。全量 192 项通过，`git diff --check` 通过；证据见 `reports/evaluations/module-status-audit.json`。
