# BTAE / EPE 项目定位与使用说明

本文回答三个问题：BTAE 是什么、EPE 解决什么工程问题、什么时候应该使用它。它补充 PRD、SPEC 和总体架构，不替代这些权威设计；当前内容描述仓库已实现的本地能力和明确的未完成边界。

## 一句话定位

BTAE（Bottom-Up Traceable Agentic Engineering）是一套让 AI Agent 按设计、契约、范围和证据持续演进软件的工程方法；EPE（Engineering Protocol Engine）是这套方法的本地协议引擎，用注册表、依赖图、门禁、验证运行器和 Evidence 把设计意图连接到代码变化。

可以把四个层次分开理解：

| 层次 | 本项目中的含义 | 主要入口 |
| --- | --- | --- |
| BTAE 方法 | 先设计、按实体组织知识、双向追溯、显式未知、证据治理和持续演进 | `AGENTS.md`、`docs/architecture/` |
| EPE 引擎 | 读取规则并执行注册、解析、映射、图、架构、验证和完成门禁 | `src/epe/`、`epe` CLI |
| Coding Agent 接入 | 在写代码前提供有限上下文和草案设计计划 | `skills/btae-coding-agent/`、`btae-mcp` |
| 宿主适配 | 把 EPE 接到本地进程、CI 或 Hermes 等执行端 | `src/epe/adapters/` |

本仓库是 Python 优先、单仓库、本地可运行的 MVP 和参考实现。它不是一个自动生成业务代码的黑盒，也不是把所有文档、测试和权限交给单一 Agent 的平台。

## 它要解决的问题

AI Agent 的短期编码速度通常不等于长期工程可维护性。多轮修改中，最容易丢失的不是语法，而是关系：这段代码依据哪个设计，影响哪些模块，是否仍符合契约，测试结果是否针对当前输入，某次“完成”是否有可信证据。

BTAE 将这些问题拆成可检查的事实：

1. **上下文漂移**：按任务、实体和依赖获取 C0–C2 上下文，并记录来源、摘要、遗漏和截断，不默认把整个仓库塞给 Agent。
2. **设计与代码脱节**：用稳定实体 ID、实现/验证映射和契约引用连接设计与文件、符号、测试。
3. **架构边界被悄悄破坏**：从 AST 和配置构建可重建依赖图，检查循环、禁止依赖、模块归属和导入边界；无法静态确认的部分显式报告 unknown。
4. **“测试通过”被过度解释**：验证运行器保存实际 argv、退出事实、JUnit 结果、环境、输入指纹和产物摘要；Evidence 的 `passed` 与 `valid` 分开计算。
5. **范围和授权不清晰**：Task、ChangeSet、审批、策略和完成门禁分别表达目标、写入范围、可信授权和当前事实；Agent 自报 approved 或 passed 不会替代证据。
6. **宿主能力被误当作信任**：本地 CLI、Hermes bridge、ACP 和 capability attestation 分开建模；协议握手成功不自动等于身份、写入隔离或操作权限可信。

## 典型使用者和场景

| 使用者 | 使用 BTAE 的目的 | 典型动作 |
| --- | --- | --- |
| 个人开发者 | 在持续使用 Agent 时保留设计依据和变更范围 | 初始化、建 Task/ChangeSet、运行 `check` |
| 团队维护者 | 在合并前审查影响、架构和证据，而不是逐行猜测 Agent 意图 | 查看 diff、架构报告、审批和 Evidence |
| Coding Agent | 在有限上下文中按项目规则设计和实施 | 调用 MCP context/plan，更新设计，执行验证 |
| 架构负责人 | 区分合法演进和实现偏差 | 维护 Architecture、Module、ADR 和策略 |
| CI/集成工程师 | 把统一的结果和门禁接到宿主或流水线 | 执行 `policy validate`、`graph build`、`architecture validate`、`check` |

它尤其适合已有一定设计和测试基础、希望逐步纳管的单仓库项目。可以先纳管关键模块，再增加实体、契约和范围；未纳管的部分必须保持明确，不能把局部检查描述为全仓库保证。

## 一次变更如何流动

```text
需求 / Issue
   ↓
Task 分类与有限上下文
   ↓
设计、契约、影响与 ChangeSet 范围
   ↓
Design Gate
   ↓
实现与映射
   ↓
Graph / Architecture / Mapping 检查
   ↓
真实验证运行与 Evidence
   ↓
Scope + Freshness + Finalize Gate
   ↓
评审、合并与后续反馈
```

四类工作流保留不同入口：Feature 从目标和验收开始；Bugfix 先复现并记录根因；Refactor 先保存基线和架构快照；Exploration 先记录问题、假设和 Prototype。它们共享实体、契约、范围和证据模型，但不被强迫使用同一种任务叙事。

## 当前可以直接使用的能力

| 能力 | 当前本地入口 | 用途 |
| --- | --- | --- |
| 初始化与状态 | `epe init`、`epe inspect` | 创建缺失治理文件、查看实体和纳管范围 |
| 设计与契约 | `epe design create/validate/approve` | 生成草案、校验契约、验证可信审批适用性 |
| 任务与范围 | `epe task ...`、`epe changeset ...` | 登记任务、激活生命周期、声明和比较 ChangeSet 范围 |
| 解析与映射 | `epe mapping validate` | 校验路径、符号和设计映射 |
| 图与架构 | `epe graph build/path`、`epe architecture validate/diff` | 重建依赖、追踪路径、检查边界、比较发现架构 |
| 验证与证据 | `epe verify`、`epe check`、`epe audit verify` | 执行授权检查、保存 Evidence、聚合完成门禁、检查审计链 |
| 上下文与影响 | `epe context resolve`、`epe impact analyze/plan` | 返回带来源的任务上下文和有预算的影响传播 |
| Coding Agent 接入 | `btae-mcp`、`$btae-coding-agent` | 读取章程/规格、生成草案计划、执行只读项目检查 |

这些入口证明的是本地检查能力和记录能力。它们不自动证明方法在真实团队中降低了缺陷、Token 或维护成本；这些效果需要独立试点、对照和消融实验。

## 它不是什么

- **不是自动批准器**：`draft`、`reviewed`、`approved` 是不同状态；审批必须绑定设计指纹和受信身份。
- **不是操作系统权限边界**：CLI 和本地锁不能阻止有权限的外部进程写文件；宿主隔离和 CI 保护需要平台证据。
- **不是动态架构的完整真值**：AST 无法覆盖所有运行时注入、反射和外部服务依赖，unknown 必须保留。
- **不是测试覆盖率替代品**：测试通过不等于设计符合；Evidence 还需要输入、版本、环境、产物和适用性检查。
- **不是默认的多语言/向量平台/图数据库**：这些属于后续或研究范围，当前实现优先确定性文件来源和可重建 JSON 索引。
- **不是已完成的 Hermes 产品集成**：Hermes 是优先适配对象，但真实身份、取消、隔离和权限仍需独立实测。

## 如何选择入口

只想运行本地工程检查时，安装包后使用 `epe` CLI；需要让 Agent 在改代码前遵循 BTAE 时，安装 `btae-coding-agent` Skill 并启动 `btae-mcp`；需要审查一次变更时，优先从 Task、实体 ID 或文件路径进入 `context resolve`、`impact analyze` 和相关门禁。所有入口都应回到仓库中的设计、契约、测试和 Evidence，而不是把 MCP 或 Agent 输出当作权威事实。

进一步阅读：

- [BTAE PRD](../intent/PRD-BTAE.md)：产品问题、用户、目标和发布条件。
- [BTAE SPEC](../intent/requirements/SPEC-BTAE.md)：数据契约、门禁、CLI 结果和验收矩阵。
- [总体架构](overview.md)：七层工程责任、治理平面与知识图谱。
- [使用指南](../standards/user-guide-mvp.md)：从安装到本地闭环。
- [Coding Agent MCP 入口](../integrations/btae-coding-agent.md)：Skill、MCP 配置和工具边界。
