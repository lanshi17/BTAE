# Policy/Workflow 统一校验

- 类型：Feature；风险：medium；涉及 MOD-007、MOD-008。
- `epe policy validate` 对架构/验证策略使用 JSON Schema，对四类 Workflow 检查类型和 required 字段；未知字段、错误类型、缺失策略或 Schema 文件不可用均返回故障。
- 该命令只校验配置，不执行检查命令、不授予权限；业务门禁仍重新读取并消费适用策略。

- 本轮结果：架构校验与验证运行入口现均使用同一策略 JSON Schema；未知字段或格式错误会在消费前拒绝，策略只被单独校验而执行端忽略的缺口已关闭。定向 19 项、全量 174 项通过，证据见 `reports/evaluations/policy-consumer-validation.json`。
