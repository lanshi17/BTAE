# WP-07：任务、权限和质量门禁

**状态：** in_progress · **里程碑：** M2 · **实施：** in_progress
**负责模块：** [governance](../../../docs/modules/governance/README.md)、core
**前置：** WP-06 · **下游：** WP-08（事实接入）、WP-09

## 1. 目标

实现四类任务记录校验、风险映射、权限判断、范围比较，以及设计/完成门禁的**纯决策**逻辑。本阶段用固定 `GateFacts` 夹具验证规则；真实检查事实在 WP-09 装配。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 加载并校验 Policy / Workflow 文档 |
| T2 | Task 四类型登记；缺验收或范围不可激活（AC-11） |
| T3 | 风险推导与 Low/Medium/High 审核要求 |
| T4 | Permission：可信身份 × 操作 × 风险 × 范围 |
| T5 | Gate Manager：Design / Finalize（及中间门禁聚合） |
| T6 | Scope：受保护范围优先；实际改动超范围阻断 |
| T7 | 固定 GateFacts 决策表测试；unknown/stale/not_run 不得完成 |
| T8 | 过期 ADR 例外无效；缺必需策略 → error 非放行 |

## 3. 拟议路径

```text
src/epe/governance/policy.py
src/epe/governance/permission.py
src/epe/governance/workflow.py
src/epe/governance/gates.py
src/epe/governance/scope.py
tests/unit/governance/
tests/fixtures/gate_facts/
```

## 4. Finalize 否决条件（最低）

任一成立即不可完成：缺适用批准（按风险）、mapping/architecture 必需项 fail 或 unknown、验证非 passed、Evidence 非 valid、超范围、索引/设计版本与决策时不一致。

## 5. 依赖约束

- governance **不** import design/verification 实现包
- 只消费 core 值对象中的 GateFacts / ApprovalAssessment 摘要
- 不启动测试、不算指纹、不解析代码

## 6. 验收映射

AC-05、AC-11 的决策部分；AC-12 的门禁逻辑预备（端到端在 WP-10）。

## 7. 完成门槛

- [ ] 决策表覆盖未执行 / unknown / stale / 超范围 / High 无授权
- [ ] 包导入约束有架构测试或静态检查草案
- [ ] 文档声明：固定事实测试 ≠ 最终系统验收
