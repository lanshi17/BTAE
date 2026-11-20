# TASK-ac09-cli-output-acceptance：CLI 输出与退出码验收

- 分类：Feature；风险：中；影响 MOD-008 CLI、MOD-009 Process、MOD-006 Verification；写入范围为 AC-09 验收测试、计划和证据。
- 依据：SPEC AC-09 要求 JSON 可解析、退出码符合约定、失败日志不污染 stdout。现有测试通过函数调用或分别检查配置错误，缺少一条真实子进程验证 stdout/stderr 分流与状态映射。
- 设计：临时工程执行真实 CLI：验证命令向子进程 stdout/stderr 各写内容并返回非零；参数错误命令；未配置 Hermes 的 host dispatch 通过能力入口仍返回结构化 unsupported（若 CLI 暴露）。每次读取完整 stdout，要求恰好一个 JSON 对象、无原始子进程日志或 traceback；stderr 只允许为空（父 CLI 不转发子进程日志）。断言 failed→1、参数错误→2、unsupported→4。
- 验收：真实 `python -m epe` 子进程边界，stdout 与 stderr 分离，结果契约字段完整，退出码稳定。仅证明 AC-09，不代表所有命令均覆盖。

- 结果：真实 CLI 子进程验证了失败子进程 stdout/stderr 只进入 Evidence、不污染父 stdout；JSON 输出始终是单一结果对象；参数错误返回 2，失败检查返回 1，能力矩阵保留 Hermes unsupported-unintegrated 状态。定向 1 项、全量 190 项通过；证据见 `reports/evaluations/ac09-cli-output-acceptance.json`。
