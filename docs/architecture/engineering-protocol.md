# 开发与治理协议

状态：v0.1 设计草案。仓库已实现本地基础门禁、Evidence 运行器、策略校验和 CI 工作流检查；CI 保护规则、远程身份和完整宿主授权仍属于后续交付。

## 1. 统一执行骨架

任务分类 → 上下文检索 → 影响分析 → 必要设计与契约 → 设计门禁 → 实现 → 验证 → 证据 → 知识同步 → 架构协调 → 按风险评审与合并。

任何入口均遵守全局约束、任务范围和证据要求，但不要求重写所有层级文档。失败时先判断是实现缺陷、契约问题、设计变化还是环境问题，再返回相应环节；不得通过降低断言或伪造状态绕过门禁。

## 2. 四类工作流

### Feature

Intent → Spec → Impact → Architecture / Class Design → Contract → Design Gate → Implement → Unit / Contract / Integration Verification → Evidence → Sync。

验收条件应能关联到具体测试或评估。实现前检查消费者与公共契约的影响；合并前检查架构演进。

### Bugfix

Bug Report → Reproduce Failure → Identify Entity → Root Cause → Fix Design → Implement → Regression → Evidence。

尽可能先建立可复现失败与回归条件。无法复现时记录诊断依据和限制，不声称已证明根因。纯内部修复不要求重写模块架构；状态模型、职责或接口改变时更新对应设计与契约。

### Refactor

Baseline → Architecture Snapshot → Dependency / Impact Analysis → Refactor Design → Implement → Regression → Architecture Comparison → Accept / Reject。

保留变更前后基线，检查公共契约、依赖循环、职责耦合和维护成本。测试通过只能证明所测行为，不能单独证明架构改善。

### Exploration

Question → Hypothesis → Prototype → Experiment → Evaluation → Decision → Formal Design → Production Implementation。

原型明确标记、隔离适用范围，记录假设、数据和实验条件。实验成功不等于生产验收通过；决定产品化后进入正式设计与验证流程。

## 3. 风险与设计门禁

| 风险 | 场景 | 目标评审方式 |
| --- | --- | --- |
| Low | 内部工具、局部且不改变契约的修复 | 自动检查 |
| Medium | 模块内部业务逻辑与协作变化 | Agent Review + 自动验证 |
| High | 公共 API、数据库结构、核心架构、安全边界 | 明确的人类授权与审批记录 |

分类根据变更内容和传播影响决定，不能由 Agent 为获得权限随意降级。已有明确授权可复用，但必须覆盖本次操作与设计版本。审批不是对未来未知变化的无限授权。

设计门禁检查实体注册、设计完整性、契约、影响分析、评审适用性和授权范围。审批记录与设计指纹绑定，审批后设计变化必须重新评估。当前的文档编写授权不应被解释为所有未来实现均已获批准。

## 4. 上下文工程

| 层级 | 内容 | 使用时机 |
| --- | --- | --- |
| C0 | 工程宪章、全局规则 | 每个任务 |
| C1 | 架构、模块边界与模块契约 | 涉及模块时 |
| C2 | 目标类、直接依赖、代码与测试 | 局部实现和修改 |
| C3 | ADR、历史变更、有效或失败证据 | 复杂变化和疑难诊断 |

优先级为实体 ID / 路径 → 图遍历 → 关键词 / BM25 → 向量检索 → 模型补充推理。输出项目附带实体 ID、源路径、源类型、版本、设计状态、新鲜度、可信度和选入原因；设置上下文预算，并显式报告遗漏或未知依赖。

## 5. ChangeSet 与并行协作

ChangeSet 记录 Task、owner、affected_entities、write_scope、protected、依赖契约版本及状态。使用 `MOD-` 作为模块前缀。

```yaml
id: CHANGE-001
task: TASK-001
owner: agent-a
affected_entities: [CLASS-001, CLASS-002, MOD-001]
write_scope:
  - docs/classes/agent/
  - src/agent/manager.py
protected:
  - docs/architecture/
dependencies:
  - entity: CONTRACT-001
    version: v1
status: active
```

共享实体或契约写入重叠时协调范围、顺序与版本。若未来实现锁，需定义锁粒度、租约、释放及异常恢复；仅声明范围不具备锁语义。执行前重新检查依赖版本，避免 Agent 根据旧契约继续写入。

## 6. 架构适应度函数

首批规则包括：Domain 不依赖 Infrastructure；指定模块不得访问被禁止的实现；模块依赖无循环；公共接口具备契约；核心类有独立设计；关键模块有集成验证。

规则包含稳定 ID、范围、严重级别和可执行检查器。例外绑定 ADR、理由、适用范围和复查条件。检查器区分不符合、无法分析与通过；无法分析不冒充通过。预期架构与发现架构不一致时，由授权决策决定更新设计还是修复实现。

## 7. 完成条件

设计与实现映射有效，所需测试和架构检查满足策略，证据与当前输入匹配，知识索引可重建，变更说明包含未验证项与限制。门禁的阻断级别由明确策略决定，不能在报告中隐去失败或警告。
