---
id: CLASS-EVIDENCE-001
type: Class
name: Evidence Runner
design_status: reviewed
implementation_status: implemented
verification_status: passed
implementation:
  - path: src/epe/verification/runner.py
    symbol: run_checks
verification:
  - test_id: TEST-CLI-001
    path: tests/acceptance/test_cli.py
---

# Evidence Runner

验证运行器只执行经过配置的参数数组，记录真实退出事实和输入前后指纹，并把产物与不可变 Evidence 分开保存。超时终止进程组；失败、故障和 stale 结果保留，不转换为通过。

命令配置来自 `engineering/policies/verification.yaml`，任务文本和模型输出不能直接构造 shell 命令。
