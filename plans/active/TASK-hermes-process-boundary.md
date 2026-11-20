# TASK-hermes-process-boundary：Hermes 桥进程边界

- 类型：Bugfix；高风险；MOD-009 Hermes adapter；范围宿主 JSON 桥、测试和宿主文档；不宣称 Hermes 已集成。
- 依据：WP-14 T2/T8、adapters §5/§6。当前 Hermes `_call` 使用 `subprocess.run` 全量缓冲 stdout/stderr，不共享 ProcessPort 的输出上限和进程组超时语义。
- 设计：Hermes 桥使用 `run_process` 参数数组、POSIX session、超时和 1 MiB 每流保留上限；退出非零、超时、取消、任一流截断、非单对象 JSON 均返回无响应并映射为 handshake-failed 或 response error。stderr 不进入协议响应；不把 handshake 声明升级为可信能力。
- 验收：正常 JSON handshake/dispatch 兼容；巨大/截断响应拒绝；超时失败且不挂起；命令错误和非 JSON 稳定返回 unsupported/error；现有能力矩阵不改变。
- 限制：宿主主动创建新 session 可逃逸；不提供身份认证、文件隔离或远程审计。状态 draft。

- 本地验证：Hermes/Process 定向测试 13 passed；完整测试 `PYTHONPATH=src pytest -q -o addopts=''`，139 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/hermes-process-boundary.json`。
