# TASK-test-evidence-eligibility：测试门禁历史证据适用性

- 类型：Bugfix；高风险；涉及 MOD-006、MOD-007、MOD-008；范围为 pytest 证据版本、有效性计算、完成门禁和直接测试。
- 依据：SPEC 测试门禁及证据有效性、verification §6。旧版仅凭终端文本的 passed 证据与新版策略命令相同，仍可能被完成门禁接受。
- 设计：新 pytest 证据标记 `pytest-junit-v1`；针对当前测试策略计算有效性时，passed 记录必须具备该协议、与实际命令匹配的运行专属摘要及经摘要验证的正通过计数。旧记录标记 unknown，保留历史执行结果但不得满足完成门禁。失败记录仍可作为有效失败事实。门禁独立检查协议，防止未经验证的旧记录直接传入。
- 验收：真实 pytest 新证据可满足测试门禁；缺协议、缺摘要、摘要篡改和命令不匹配不能通过；旧失败保留可用性。测试不能证明日志或记录在不可信存储中免于伪造；设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，86 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/test-evidence-eligibility.json`。
