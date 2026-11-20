# TASK-ac08-evidence-validity-acceptance：产物与环境有效性验收

- 分类：Feature；风险：中；影响 MOD-006 Verification、MOD-007 Governance、MOD-008 CLI；写入范围为 AC-08 验收测试、计划和证据。
- 依据：SPEC AC-08 要求产物摘要修改为 invalid，环境信息不足为 unknown。现有测试直接调用 `evidence_validity`，缺少通过真实 CLI 生成 Evidence、篡改产物并让 `check` 重新计算的场景。
- 设计：临时工程生成真实通过 Evidence，修改其 output.log 后运行 check，要求 validity=invalid 且综合门禁阻断；恢复产物后删除 Evidence 的 environment 字段，运行 check，要求 validity=unknown 且门禁仍阻断。通过同一任务和检查 ID 断言最新 Evidence，不依赖运行器重新生成记录。
- 验收：CLI 返回 JSON，Evidence 文件保留真实记录；invalid 与 unknown 不互相混淆，也不能被 finalize gate 当作 valid passed。此处不证明远程产物存储不可变。

- 结果：真实 CLI 生成通过 Evidence 后，篡改 output artifact 使其 validity=invalid；恢复产物但删除环境信息使其 validity=unknown；两种状态均不能满足门禁。定向 1 项、全量 189 项通过；证据见 `reports/evaluations/ac08-evidence-validity-acceptance.json`。
