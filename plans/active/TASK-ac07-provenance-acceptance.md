# TASK-ac07-provenance-acceptance：工作树与 Evidence 新鲜度验收

- 分类：Feature；风险：中；影响 MOD-003 Graph、MOD-006 Verification、MOD-008 CLI、MOD-009 Git；写入范围为验收测试、计划和证据。
- 依据：SPEC AC-07 要求无提交/脏工作树记录真实 provenance，源/契约/测试变化后 Evidence stale。现有单测验证 Git facts 和 EvidenceValidity 算法，缺少同一 CLI 仓库中生成并重新评估 Evidence 的闭环。
- 设计：临时工程初始化真实 Git 仓库但不提交；准备 Class、契约、实现映射、pytest 检查和 ChangeSet，完成一次通过 Evidence。断言 commit=null、dirty=true、未跟踪源路径可见。分别修改实现源、仍合法的契约 YAML 注释、仍可通过的测试源码；每次变更后重建图并运行 check，确认旧 Evidence 显示 validity=stale。范围覆盖设置为允许这些修改，避免 scope 门禁混淆新鲜度断言。
- 验收：CLI stdout 始终为结构化 JSON；三种变更分别导致同一运行 Evidence stale，Git provenance 保留真实无提交/未跟踪事实。此处不证明远程 Git 身份真实性。

- 结果：真实 CLI 在无提交脏工作树记录 commit=null、dirty 和未跟踪目录；实现源码、契约 YAML 与测试源码分别变化后，既有 Evidence 在 `check` 结果中标记 stale。契约实体 round-trip 修复后定向 7 项、全量 188 项通过；证据见 `reports/evaluations/ac07-provenance-acceptance.json`。
