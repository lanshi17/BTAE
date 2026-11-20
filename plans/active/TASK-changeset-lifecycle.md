# TASK-changeset-lifecycle：ChangeSet 状态迁移

- 类型：Feature；高风险；MOD-007 governance、MOD-008 CLI、MOD-009 持久化；保留现有创建与基线测试。
- 依据：SPEC §3.3、governance §6、WP-07 T2/T6。当前 ChangeSet 文件虽有 status 字段，但无迁移接口，且校验只允许 planned/active；完成或中止无法留下 revision 变化。
- 设计：新增 `epe changeset transition CHANGE-ID activate|complete|abort`。在 EPE 写锁内读取记录并校验关联任务、基线摘要和 expected_revision。`planned→active`；`active→completed` 先重新比较基线和 write/protected 范围，任一超范围或声明无效即阻断；`planned/active→aborted` 保留历史记录并递增 revision。非法状态迁移和 revision 冲突不写文件。记录更新采用临时文件原子替换，状态字段仍为权威 ChangeSet 声明。
- 兼容：保留现有 create 对 `status: active` 的兼容输入；新流程默认模板为 planned，建议先创建再 activate。旧已登记记录可继续通过现有综合检查。
- 验收：四条合法/非法迁移、完成范围阻断、revision 冲突、写入冲突和重读持久化均有端到端测试。
- 限制：ChangeSet 文件不是跨进程租约；写锁不能约束外部编辑器，状态审计仍依赖本地审计链。状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，133 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/changeset-lifecycle.json`。
