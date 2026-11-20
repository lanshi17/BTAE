# TASK-ac02-registry-diagnostics-acceptance：Registry 诊断子进程验收

- 分类：Feature；风险：低；影响 MOD-001 Core、MOD-002 Parsers、MOD-008 CLI；写入范围为验收测试、计划和证据。
- 依据：SPEC AC-02 要求重复 ID、重复 YAML 键、悬空边分别诊断。现有覆盖主要通过单元调用，YAML CLI 负例只包含不可哈希键。
- 设计：使用真实 CLI 子进程和临时工程分别写入三种非法文档，调用 `graph build`；每例要求非零退出、单一 JSON stdout、指定诊断码/路径/行号，且 `published=false`。每个场景隔离输入，防止一个诊断遮蔽另一个。
- 验收：分别得到 `EPE-ENTITY-DUPLICATE`、`EPE-YAML-PARSE`、`EPE-RELATION-DANGLING`，不出现 traceback，不发布图快照。仅证明 AC-02 的三种解析/注册输入，不替代全量验收。

- 结果：真实 CLI 子进程分别得到重复实体、重复 YAML 键、悬空关系的独立结构化诊断，均未发布图。定向 1 项、全量 178 项通过；证据见 `reports/evaluations/ac02-registry-diagnostics-acceptance.json`。
