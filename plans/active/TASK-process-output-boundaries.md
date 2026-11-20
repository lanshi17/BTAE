# TASK-process-output-boundaries：子进程输出与生命周期边界

- 类型：Bugfix；高风险；MOD-009 ProcessPort 和 MOD-006 结果映射；只修改进程适配器、最小消费方与直接测试，保护其他工作树改动。
- 依据：adapters §5、WP-08 T2/T8。现有 `communicate()` 将 stdout/stderr 全量缓冲，可能由目标进程耗尽 EPE 内存；超时仅记录 leader 结果，缺少截断事实和取消接口。
- 设计：POSIX 使用非阻塞 pipe/select 持续排空 stdout/stderr，只保留每流配置字节上限并记录独立截断标志；超时或取消时向本次 session/process group 发 SIGTERM，宽限期后 SIGKILL，并继续排空到关闭。保留 argv、退出码、耗时和原有超时字段，增加 cancellation 与输出截断事实；验证报告将截断标记写入 Evidence provenance，pytest 结构化结果仍从独立 XML 文件解析。非 POSIX 的强制进程组语义不作承诺。
- 验收：超过输出上限时内存保留受限且两条流均完整排空；超时/取消杀掉孙进程；正常退出与命令启动失败保持明确；Evidence 记录 stdout/stderr 截断。
- 限制：不合作进程可通过新 session 逃逸；操作系统不可中断状态可能延迟终止；限额只限制保留内容，不限制子进程输出总字节。设计状态 draft。

- 本地验证：目标测试 `PYTHONPATH=src pytest -q -o addopts='' --cov=epe.adapters.process --cov-report=term-missing tests/unit/test_process.py tests/integration/test_process_lifecycle.py tests/integration/test_evidence_snapshot_integrity.py`，20 passed，process.py 覆盖率 84%；全套 `PYTHONPATH=src pytest -q -o addopts=''`，120 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/process-output-boundaries.json`。
