# TASK-audit-concurrent-append：审计链追加完整性

- 类型：Bugfix；高风险；范围 MOD-009 审计文件追加与校验、相关测试和模块设计；不改变审批授权语义。
- 依据：WP-08/14 与 adapters §7。当前多个写者可能读到相同尾记录并产生重复序号；损坏链仍可继续追加，部分行和短写未安全处理。
- 设计：Linux 本地文件以同一文件描述符加排他 advisory flock，锁内完整检查链和终止换行后计算新事件；完整写入并 fsync。读取校验取共享锁；坏链拒绝追加。拒绝最终路径为符号链接。写入异常不回滚已写字节，下次校验必须发现未完成记录。
- 验收：多进程真实并发追加后序列连续；破损、缺终止换行和非法 JSON 不被追加；部分写入处理；正常追加/读取回归。
- 限制：advisory 锁不约束其他程序或文件替换；链无法发现整个文件或尾部被删除，也不能认证被重写的全链。审批文件与审计文件之间尚无跨文件事务；本设计为 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，97 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/audit-concurrent-append.json`。
