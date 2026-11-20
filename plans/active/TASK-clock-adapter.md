# TASK-clock-adapter：统一 UTC 与单调时钟端口

- 类型：Feature；中风险；MOD-009 Clock Adapter、MOD-006 runner、MOD-009 audit 的时间产生；保护其他已有修改。
- 依据：adapters §2/§3/§7、core ClockPort。当前端口无实现；Evidence 与 Audit 各自直接调用 wall clock，无法通过注入稳定验证时间语义。
- 设计：新增 `SystemClock`，提供 UTC RFC3339 `Z` 时间和单调秒数；ClockPort 增加单调接口。runner 和 audit 默认装配 SystemClock，并允许测试/应用注入 ClockPort。耗时仍由 Process adapter 单独用单调时间测量，不能使用 wall clock。
- 验收：系统 UTC 始终带 `Z`；注入时钟能确定性控制 Evidence 和 Audit 时间；时间回拨不影响 ProcessResult duration 的单调语义；既有默认调用兼容。
- 限制：本地时钟不提供可信时间戳或抗篡改证明。状态 draft。

- 本地验证：定向时钟/进程/Audit/Evidence 测试 31 passed；完整测试 `PYTHONPATH=src pytest -q -o addopts=''`，130 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/clock-adapter.json`。
