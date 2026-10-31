# BTAE Agent 工作协议

## 项目定位与当前阶段

BTAE（Bottom-Up Traceable Agentic Engineering）是面向 AI Agent 的通用工程方法：自下而上构建、规格约束、双向追溯、证据验证与持续演进。工程协议引擎称为 EPE（Engineering Protocol Engine）。

本仓库目前处于规范初始化阶段，没有正式实现、构建系统或测试命令。用户提供的深度优化方案是初始需求依据；不要将目标能力、CLI 示例或参考项目描述为已经实现。优先完成可实施的工程规格，再按 MVP 范围开发。Hermes 是优先集成对象，但核心协议必须独立于 Hermes、Codex CLI、Claude Code 等执行端。

默认使用中文编写设计文档与交流，代码标识符、实体 ID 和机器字段使用英文。研究结论及其数字未经查证不得当作已验证事实；记录来源、适用条件和待核实项。

## 六项工程原则

1. 重要实现必须有明确设计依据；先设计后实现。
2. 按逻辑实体组织知识，禁止机械地为每个代码文件创建一份文档。核心类保留独立类设计文档。
3. 设计、契约、代码、测试和证据建立双向追溯。
4. 顶层架构约束引导底层构建；比较预期架构与发现架构，并通过 ADR 协调演进。
5. 完成声明必须有可追溯证据，测试覆盖率不能代替设计符合度。
6. 按任务检索上下文、分析影响、控制修改范围，避免默认遍历并加载全部文档。

## 七层责任与横向设施

| 层 | 责任 | 规划位置 |
| --- | --- | --- |
| L0 | 工程宪章、原则、安全与全局约束 | `docs/constitution/` |
| L1 | 目标、规格、行为与验收条件 | `docs/intent/` |
| L2 | 架构、领域、模块边界与 ADR | `docs/architecture/`、`docs/modules/` |
| L3 | 组件、类设计与机器契约 | `docs/components/`、`docs/classes/`、`docs/contracts/` |
| L4 | 正式实现 | `src/` |
| L5 | 测试、评估和验证证据 | `tests/`、`reports/` |
| L6 | 变更、维护、归档和技术债务 | `plans/`、`archive/` |

这些层是责任划分，不是必须逐层执行的瀑布阶段。

- Governance Plane：协议、权限、生命周期、门禁和架构适应度函数。
- Engineering Knowledge Graph：实体、关系、依赖、影响分析和证据索引。
- 两者保持边界，避免形成包办所有职责的单一 Agent。

## 权威来源与目录边界

- Markdown 负责设计意图、职责、理由与边界；YAML、JSON Schema、OpenAPI 等负责机器可验证约束；代码负责实际实现；测试负责行为验证；执行产物负责证明某次验证结果。
- `docs/standards/` 存放工程、文档、编码、测试和 Agent 协议规范及模板。
- `engineering/schemas/`、`engineering/policies/`、`engineering/workflows/` 存放治理系统定义。
- `.engineering/` 只存可重建的自动索引与缓存，禁止手工修改，也不能用作权威知识源。
- `plans/active/`、`plans/backlog/`、`plans/completed/` 管理任务计划；`archive/` 保留已替代的设计、决策和迁移记录。
- 按实际需求建立目录，避免为了匹配目标结构提前生成空文件和空模块。

## 实体、关系与状态

以 Class / Component 为细粒度设计实体，Module 为组织协作实体，Architecture 为全局约束实体，Evidence 为完成证明，Agent Protocol 为执行机制。简单项目可省略 Component 层。

- 使用稳定、不可复用的 ID，如 `PROJ-BTAE`、`INTENT-001`、`SPEC-001`、`ARCH-001`、`MOD-001`、`COMP-001`、`CLASS-001`、`CONTRACT-001`、`TASK-001`、`CHANGE-001`、`TEST-001`、`EVIDENCE-001`、`ADR-001`。统一使用 `MOD-`，不要混用 `MODULE-`。
- 重命名或移动文件不得改变逻辑实体身份。通过 implementation 和 verification 映射关联一个或多个文件及符号。
- 标准关系：`contains`、`realizes`、`specifies`、`depends_on`、`conforms_to`、`verified_by`、`evidenced_by`、`constrained_by`、`supersedes`、`affects`。在 Schema 中明确各关系方向、合法端点及基数，避免仅凭动词猜测方向。
- 关系记录来源、定位信息、可信度和验证状态。显式声明、静态发现、模型推断属于来源类型；是否经过验证属于独立属性。推断关系未经确认不得作为确定事实或审批依据。
- 分离设计状态、实现状态、验证结果与证据有效性。设计至少区分 `draft/reviewed/approved`；实现区分 `not_started/in_progress/implemented`；验证至少区分 `pending/passed/failed`；证据有效性区分 `valid/stale/invalid/unknown`。后续扩展必须通过统一 Schema 定义。
- 审批绑定明确的设计版本或内容指纹；设计改变后重新评估审批。不得把初始化文档或 Agent 自述等同于已批准设计。

## 每次任务的执行协议

1. **分类与定位**：确定 Feature、Bugfix、Refactor 或 Exploration；读取全局规则、目标模块、直接依赖、相关契约与测试，必要时补充 ADR 和历史证据。
2. **声明范围**：记录任务、受影响实体、写入范围、受保护路径、依赖契约及风险级别。先检查现有改动，不覆盖其他工作。
3. **影响分析**：同时考虑设计到代码、代码到设计的传播；追踪契约消费者、测试与架构规则。静态分析无法确定的动态依赖应明确标注。
4. **设计与门禁**：在实现前补齐必要设计、机器契约和可验证验收条件。内部低风险修改采用自动检查；模块业务变更增加评审；公共 API、数据库结构、安全边界和核心架构变更需要明确授权。已有任务授权持续有效，不重复索取授权；不得伪造审批。
5. **实现与验证**：只修改任务范围内工件，执行与变更相关的检查。发现职责、接口或状态模型变化时同步设计；纯内部修复无需重写无关规格。
6. **证据与同步**：保存真实执行结果、检查知识映射、更新可生成索引，并报告完成项、失败项和未验证项。未满足门禁不能宣称完成。

工作流入口：

| 类型 | 必要步骤 |
| --- | --- |
| Feature | Intent → Spec → Impact / Design → Contract → Implement → Verify |
| Bugfix | Reproduce → Affected Entity → Root Cause → Fix Design → Implement → Regression |
| Refactor | Baseline → Architecture Snapshot → Impact → Design → Refactor → Regression / Architecture Comparison |
| Exploration | Question → Hypothesis → Prototype → Experiment → Evaluation → Decision |

探索产物标记为 Prototype；进入正式实现前补齐正式设计和验收。不要强迫未知方案提前编造完整生产设计。

## 验证、证据与架构治理

- 文档结构用 Schema，Python 符号用 AST，接口用签名和契约验证，业务行为用测试，依赖边界用静态规则，性能用基准测试。
- 漂移检查分为 D0 文件/符号、D1 接口、D2 行为、D3 语义/架构。LLM 可提出 D3 疑点，不能单独充当通过证明。
- 架构规则应覆盖禁止依赖、模块循环、公共契约、核心类设计和关键模块集成验证。规则例外必须记录理由、范围及相关 ADR。
- Evidence 至少关联目标实体、实际命令、执行结果、时间、代码版本或工作树指纹、测试版本、环境、源代码与契约指纹、产物位置。无 Git 提交时如实记录，不填写虚构提交号。
- 将验证执行结果与证据当前有效性分开：曾经 passed 的结果可能因依赖变化而 stale。根据受影响范围失效证据，保留历史结果。
- 区分“规划了检查”“本地已运行检查”“CI 已运行并强制门禁”。当前仓库没有可用测试或 CI；建立后将实际命令写入项目文档，不假设 `pytest` 或 `epe` 已可运行。

## 上下文与协作

检索顺序为显式实体 ID / 路径、图邻接与影响关系、关键词检索、语义检索、模型补充推理。上下文携带来源、版本、状态、新鲜度与可信度，区分当前设计、代码事实、历史记录和推断。

如任务明确采用多 Agent 并行，以 ChangeSet 声明实体和写入范围，对共享契约进行版本协调；范围声明不等于实际锁，只有工程系统实施锁定后才能声称隔离有效。

## 实施路线与完成标准

- V0.1：冻结工程规范、目录约定、实体与关系 Schema、文档模板、四类工作流、Agent Protocol、CLI 接口及验收标准。
- V0.2：优先实现实体注册、文档解析、代码解析、映射校验、依赖图、设计门禁、测试门禁、证据记录八项 MVP 能力，并接入 CI。
- V0.3：增量影响分析、知识图谱查询、Context Resolver；初期采用文件权威源与可重建内存图 / JSON 索引，不提前引入图数据库或向量平台。
- V1.0：完善多工作流、证据治理、架构演进和 Hermes 等 Agent 适配。

`epe init/inspect`、任务管理、上下文检索、影响分析、设计校验与审批、映射校验、图构建、架构校验、验证、同步和综合检查均为目标接口，具体语法以未来批准的 CLI 规格为准。

交付时说明实际修改、验证命令与结果、证据位置和剩余限制。方法有效性属于待检验研究假设；通过初始开发、需求变更、长期演进及消融实验评估，不预先声称优于现有 SDD。
