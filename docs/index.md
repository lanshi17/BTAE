# BTAE 工程文档

Bottom-Up Traceable Agentic Engineering：自下而上构建、规格约束、双向追溯、证据验证与持续演进的智能体工程体系。

本组文档依据项目初始方案整理，版本为 **v0.1 设计草案**。它描述目标架构，不代表工具已实现、规范已冻结或设计已获审批。仓库尚无正式 EPE 实现、自动化门禁或 CI。

## 阅读顺序

产品与实现依据：

- [BTAE PRD](intent/PRD-BTAE.md)：用户、问题、产品范围、优先级与发布条件。
- [BTAE SPEC](intent/requirements/SPEC-BTAE.md)：MVP 数据契约、接口、门禁、证据与验收矩阵。

架构设计：

1. [总体架构](architecture/overview.md)：问题、原则、七层体系、横向设施与工程闭环。
2. [工程知识模型](architecture/knowledge-model.md)：实体、关系、权威来源、状态、追溯和证据。
3. [EPE 模块与依赖边界](architecture/boundaries.md)：职责、数据流、依赖规则与 Agent 适配。
4. [开发与治理协议](architecture/engineering-protocol.md)：四类工作流、风险门禁、上下文、协作和架构演进。
5. [目录与工件组织](architecture/repository-layout.md)：目标目录和各类工件的维护边界。
6. [实施路线与验收](architecture/implementation-roadmap.md)：MVP、CLI 目标接口、质量指标及研究验证。
7. [参考资料](architecture/references.md)：借鉴来源及尚未核实的研究主张。

[AGENTS.md](../AGENTS.md) 是 Agent 的执行入口；本目录承载详细设计。后续变更应保持两者一致，机器约束最终落实到 `engineering/` 下的 Schema、Policy 和 Workflow。
