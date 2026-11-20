# TASK-task-schema-strictness：任务契约严格校验

- 类型：Bugfix；中高风险；范围 MOD-007 Task 校验、相关测试和治理设计；保留已有工作。
- 依据：WP-01 D-14、WP-07 T2/T7、governance §3。当前 `validate_task` 只检查必填字段与部分枚举，未知字段会静默进入 raw，revision 也可被转换为负数或非整数。
- 设计：允许字段集合固定为 schema_version/id/type/objective/acceptance/risk/target_entities/changeset/status/revision 及四类工作流所需 `baseline_manifest`、`reproduction`、`hypothesis`；未知顶层字段返回错误。schema_version 必须为 1；revision 必须是正整数且不能是 bool；字段类型必须正确。保留 raw 供工作流读取，但只在校验通过后构造 Task。
- 验收：未知字段、错误 schema、布尔/负/字符串 revision、错误数组元素均拒绝；合法四类任务和现有工作流继续通过。设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，101 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/task-schema-strictness.json`。
