# TASK-pytest-result-evidence：测试执行结果校验

- 类型：Bugfix；风险：高；范围 MOD-006 运行器、直接测试与设计；保持其他工作。
- 依据：SPEC 测试门禁、WP-08 和 verification §6。当前通过任意进程打印 `1 passed` 即可冒充执行过 pytest。
- 设计：pytest 测试检查仅接受与运行器同一 Python 解释器的 `-m pytest` 形式，由运行器增加独立 JUnit XML 输出；仅在退出成功且 XML 中存在实际通过的 testcase、没有 failure/error 时判 passed。跳过、空报告、缺失或解析失败不得通过。持久化计数摘要及摘要指纹而不保存可能含敏感输出的 XML；记录实际执行参数，同时保留策略命令以供门禁匹配。旧终端文本不能单独证明测试执行。
- 验收：真实通过、失败、全跳过、零测试；任意脚本打印伪通过摘要不能通过；用户指定 XML 输出冲突拒绝；验证证据实际命令及摘要。
- 局限：Python 环境、测试代码与 pytest 插件需可信；结构化报告不能抵御恶意测试伪造，也不能证明测试质量。设计为 draft，不代表审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，85 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/pytest-result-evidence.json`。
