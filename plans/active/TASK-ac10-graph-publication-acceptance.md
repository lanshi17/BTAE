# TASK-ac10-graph-publication-acceptance：图快照发布端到端验收

- 分类：Feature；风险：高；影响 MOD-003 Graph、MOD-008 CLI、MOD-009 Storage；写入范围为 AC-10 验收测试、计划和证据。
- 依据：SPEC AC-10 要求删除索引后重建一致、失败不发布半图、并发写入返回冲突。已有单元/集成测试直接调用 builder 并注入写失败；本任务补真实 CLI 的索引删除和锁冲突。
- 设计：临时工程执行真实 `graph build`，记录 current generation 和 graph digest；删除 `current.json` 与兼容根视图后重建，要求 digest 相同且 generation 目录完整。随后创建 `.engineering/.write.lock` 模拟第二 EPE 写者，修改源码触发新构图，要求退出码 5、JSON 中 `EPE-WRITE-CONFLICT`，旧 current 字节不变，无临时 generation 被视为 current。测试不 mock builder。
- 验收：真实 subprocess stdout 单 JSON；重建内容等价；锁冲突不覆盖旧指针、不返回 published=true。断电持久性和外部进程 advisory lock 仍属限制。

- 结果：真实 CLI 删除 current/兼容索引后重建得到相同 generation digest；持有写锁时新构图返回退出码 5 和 `EPE-WRITE-CONFLICT`，旧 current 字节与 generation 保持不变。定向 1 项、全量 191 项通过；证据见 `reports/evaluations/ac10-graph-publication-acceptance.json`。
