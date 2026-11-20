# TASK-malformed-input-diagnostics：异常元数据诊断

- 分类：Bugfix；风险：中；影响 MOD-002 YAML/Markdown、MOD-001 Registry 和 MOD-007 Task 校验；写入范围为解析和校验器、直接回归测试及文档；保留既有工作。
- 依据：SPEC §5、parsers §4、WP-03。不可哈希 YAML 键、列表类型的实体 type/status、Task type/risk/status 等当前可能抛出未处理异常，中断 CLI 而不是生成结构化诊断。
- 设计：YAML 不可哈希键转换为带位置的解析错误；实体和任务校验在集合/映射查询前检查字段类型，拒绝非字符串键和错误集合类型；显式错误值不能通过 `or []` 当成空数组；关系来源类型也先做类型检查。错误输入不得发布完整 Registry，其他合法实体仍保留供诊断。
- 验收：单元及真实 CLI 用非法列表/对象和不可哈希键验证无 traceback、诊断定位和退出非零；合法数据回归通过。
- 限制：此更改不提供通用不可信 YAML 资源限额；设计为 draft。

- 本轮结果：修复不可哈希键、错误枚举类型、显式错误数组值及关系元数据；CLI 集成回归覆盖实体与 YAML 解析失败。定向 22 项、全量 154 项通过；证据见 `reports/evaluations/malformed-input-diagnostics.json`。此任务的设计仍为 draft，证据仅覆盖所列场景。
