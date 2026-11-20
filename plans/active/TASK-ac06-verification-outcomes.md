# TASK-ac06-verification-outcomes：验证结果类型真实 CLI 验收

- 分类：Feature；风险：中；影响 MOD-006 Verification、MOD-008 CLI、MOD-009 Process；写入范围为验收测试、计划和证据。
- 依据：SPEC AC-06 要求通过、失败、零测试、超时和缺命令有不同且真实结果。现有测试主要直接调用 `run_checks`，仅断言部分结果，没有同一 CLI 边界的区分验收。
- 设计：对隔离临时工程调用真实 `python -m epe verify` 子进程。成功命令、非零命令、pytest 零收集、pytest 全 skip、pytest 断言失败、超时命令和不存在可执行文件分别生成独立 Evidence；断言命令退出码、Evidence result、termination_reason、pytest counts 与产物有效性一致。命令都使用 argv 数组；超时用真实子进程，不 Mock。JUnit testcase 事实优先于 pytest 总退出码，零收集与断言失败采用不同结果。
- 验收：五种事实不互相混淆；每次均产生一个可定位 Evidence，成功仅返回 passed/valid；零通过测试不得成功；测试断言收集事实与普通失败可区分。

- 结果：真实 CLI 的通过、普通失败、pytest 零收集、全 skip、断言失败、超时和缺失命令均形成可区分 Evidence；零收集与断言失败不再混为一类。定向 6 个 AC 场景、验证/证据回归共 20 项通过；全量 186 项通过。证据见 `reports/evaluations/ac06-verification-outcomes.json`。
