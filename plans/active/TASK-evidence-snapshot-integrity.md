# 验证证据与图快照新鲜度修复

- 类型：Bugfix；风险：high（完成门禁与证据完整性）。用户已授权持续实现全部模块；不代表设计已获审批。
- 目标实体：MOD-001、MOD-003、MOD-006、MOD-008；依据 SPEC-001 第 4–7 节及 AC-06、AC-07、AC-10、AC-12。
- 写入范围：`src/epe/core/fingerprint.py`、`src/epe/graph/builder.py`、`src/epe/verification/runner.py`、`src/epe/cli.py`、验证策略 Schema、相关测试和本记录。保护其他既有用户改动；不修改 `.engineering/` 以外的派生索引。
- 根因：Evidence 重算忽略运行时已记录的 stale；图读取未比较输入指纹；测试退出零但没有测试执行证明时可能被判通过；验证有诊断时 CLI 可能仍报告成功。
- 修复设计：运行时 stale 不可被同一记录的重算覆盖；读取图时校验内容摘要、完整性与当前 manifest，不匹配拒绝消费；测试检查需明确支持的执行结果证据；验证错误优先于通过。失败保留原始 Evidence。
- 验收：真实子进程修改输入后即使当前等于运行后输入也保持 stale；修改图输入或篡改图后读取失败；无测试结果或零测试均不可通过；配置含无效检查时不能显示 passed；已有正常检查不回归。
- 限制：本任务不解决可信身份、审批撤销、全部策略覆盖、快照多文件原子发布或完整 V0.2–V1.0 验收。

## 本地验证记录

执行 `PYTHONPATH=src python -m pytest -q`，20 项通过；执行记录在 `reports/evaluations/evidence-snapshot-integrity.json`，包含时间、工作树状态、命令输出和相关输入摘要。该报告是本次本地测试结果，不表示 CI 已运行或全部验收条件已满足。图构建竞态、完整授权链、策略 Schema 实际执行及安全边界仍需后续验证。
