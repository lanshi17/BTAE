# TASK-changeset-gate-compatibility：ChangeSet 完成门禁与基线兼容

- 分类：Bugfix；风险：高；影响 MOD-007/MOD-008、Task/ChangeSet、范围基线和验证证据；写入范围限于治理、CLI、直接测试及设计记录，保护现有工作树。
- 依据：SPEC §3.3、六项工程原则、WP-07；上轮 ChangeSet `complete` 只核对范围，可能在测试或设计失败时声明 completed；基线摘要改动未版本化，旧记录会失效。
- 设计：完成操作必须在 EPE 锁内确认 ChangeSet 与 Task 双向绑定、Task active、ChangeSet active、范围校验通过，并运行现有综合 `cmd_check`；门禁后重新读取 Task 和 ChangeSet 指纹，改变则阻断。未知、失败或过期证据均不能完成。旧基线仅在其原始声明（含状态/修订）仍能逐字验证时允许只读范围检查；旧基线不得迁移生命周期，因为旧摘要绑定可变状态，需要重新登记而不是伪造迁移。新基线算法继续以不可变声明绑定范围。
- 验收：无测试证据、错误任务绑定及变化范围均阻断且状态不变；真实验证后完成；旧基线可读，旧基线迁移阻断；范围声明篡改拒绝。
- 限制：本地写锁不约束外部进程；审批/证据文件的远程防篡改仍未解决。设计 draft，不表示已批准。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，148 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/changeset-gate-compatibility.json`。
