# TASK-module-coverage-gate：模块覆盖不足的架构门禁

- 分类：Bugfix；风险：中；影响 MOD-003 Graph、MOD-006 Verification、MOD-008 CLI；写入范围为架构校验、相关测试与设计文档。保留工作区既有成果。
- 根因：存在 Module 和 Python Source，但未配置模块归属时，`module_coverage=unconfigured` 仍返回架构 pass，可能将未执行的模块循环检查作为完成依据；`unknown_is_blocking=false` 时，静态盲区也被标成 pass。
- 设计：若图同时包含 Module 与纳管 Source 且归属为 unconfigured/unknown，报告模块覆盖盲区；partial 和静态盲区一并保留。默认 unknown 阻断；显式 `unknown_is_blocking: false` 时诊断为 warning、报告 status=unknown，由策略决定是否允许门禁继续，不能称为 pass。没有模块或没有 Python Source 时不强制模块归属。已发现的真实架构违规始终 fail，与盲区策略独立。
- 验收：真实 CLI 展示无配置时阻断、显式允许 unknown 不称为 pass，以及配置完整时可判定；单元测试覆盖真实违规优先、动态盲区和无模块适用范围。设计 draft。

- 结果：无模块归属时不再将覆盖不足标为 pass；放宽策略保留 unknown 和 warning，非法布尔配置被拒绝。真实 CLI 与单元测试定向 9 项、全量 165 项通过。证据见 `reports/evaluations/module-coverage-gate.json`。
