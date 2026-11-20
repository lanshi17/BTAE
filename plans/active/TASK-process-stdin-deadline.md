# TASK-process-stdin-deadline：受控子进程标准输入

- 分类：Bugfix；高风险；影响 MOD-009 进程适配器、Hermes 桥；范围为两者、直接回归测试与设计记录；保留其他未提交工作。
- 现象：输入在排空输出和超时监控启动前同步写入，子进程不读取或先写满 stdout 会造成死锁；无缓冲 `write` 还可能短写，导致请求截断后误认为有效。
- 依据：adapters §5、WP-14 T2；设计状态 draft。输入、输出和超时必须并发进行；stdin 写入必须循环处理短写和 BrokenPipe，未完整发送标记 `stdin_incomplete`，Hermes 必须拒绝该响应。超时和取消覆盖输入阶段；现有输出上限与进程组语义保持。
- 验收：真实子进程拒绝读取大输入时在超时内退出；先输出后读取的大量双向数据无死锁，输入完整；提前关闭 stdin 的零退出子进程标记未完整；Hermes 不接受未完整发送的请求。
- 风险与边界：外部子进程自行脱离 session 仍可逃逸；无超时时无界等待为调用方设置的行为，线程不能认证输出来源。

- 回归复现：修复前不读取 stdin 的子进程导致外层 4 秒超时；修复后相关场景通过。完整测试 `PYTHONPATH=src pytest -q -o addopts=''`：145 passed in 7.62s；`git diff --check` 通过。证据：`reports/evaluations/process-stdin-deadline.json`。
