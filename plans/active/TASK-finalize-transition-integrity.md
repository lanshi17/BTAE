# 任务完成迁移与真实门禁绑定

- 类型：Bugfix；风险：high；影响 SPEC-001、MOD-007、MOD-008、Task 和 ChangeSet。用户授权持续实现；不代表设计被批准。
- 根因：CLI 接受自由文本 `--gate passed`，可在缺设计、范围和测试证据时直接把任务标记为 completed；任务创建也可直接声明 completed。
- 修复：创建任务只允许 planned；完成迁移在持有本地 EPE 写锁期间重新加载任务、核对期望 revision，运行实际只读综合检查，并在写入前再次核对任务和检查结果；不得信任调用者提供的门禁字符串。拒绝旧 `--gate` 参数，返回明确诊断。使用当前检查不代表宿主不可绕过。
- 验收：伪造 passed、缺证据、缺 ChangeSet 和过期 revision 不能完成，文件保持原样；真实设计→范围→验证→门禁通过后才能完成；重复完成被拒绝。验证并发写入只能覆盖 EPE 锁参与者，外部写入依然需宿主隔离。

## 本地验证

`PYTHONPATH=src python -m pytest -q`：65 项通过；包含伪造 `--gate passed`、直接创建 completed、缺证据、版本冲突和真实临时仓库通过门禁后完成的场景。执行记录见 [finalize-transition-integrity.json](../../reports/evaluations/finalize-transition-integrity.json)。本次未实测外部宿主隔离、远程 CI 或所有门禁事实的可信度。
