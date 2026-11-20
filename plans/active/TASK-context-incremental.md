# 上下文缓存与增量图计划

- 类型：Feature；风险：medium；涉及 MOD-003、MOD-004、MOD-008；依据 WP-12/WP-13 和上下文/图模块设计。
- 上下文缓存键包含任务完整声明、图摘要、设计/代码/策略/审批/Evidence manifest 与预算；缓存只位于 `.engineering/`，失效时重新装配。图 stale 时上下文命令保留诊断并不消费旧关系。
- 增量计划比较两个完整图的输入 manifest，保留新增、修改、删除路径；快照缺失、不完整、Schema 或解析器版本变化时回退全量。计划不伪装为已完成的增量重解析或删除节点的完整影响恢复。
- 本地验收覆盖缓存命中/失效、Evidence 变化、设计变化、删除路径、解析器回退和预算截断。
- Context Bundle 当前还提供 C3 历史 ADR/归档与任务 Evidence 摘要，并在 C0 被预算裁掉时显式返回 `incomplete`。
- `build_graph_incremental` 现在会读取旧快照中的序列化代码事实，仅解析变化的 Python 路径；缺少旧事实、Schema 或解析器变化时回退全量，增量摘要必须与全量重建等价。图发布使用临时 generation 和 current 指针。

## 本地验证

当前全套 `PYTHONPATH=src python -m pytest -q`：51 项通过；Context CLI 缓存命中/图 stale、输入 manifest 失效、增量回退、增量摘要等价和 generation 发布测试见 [执行记录](../../reports/evaluations/iteration-all-modules-004.json)。
