# EPE 模块与依赖边界

状态：v0.1 设计草案。模块是逻辑边界，首版不要求每个职责对应独立包或服务。

各模块详细接口、异常处理、验证和交付安排见[模块设计索引](../modules/README.md)；实施顺序见[工作包计划](../../plans/backlog/BTAE-implementation-plan.md)。模块索引中的允许导入表是本边界的细化，尚未转为可执行 CI 规则。

## 1. 职责分配

| 模块 | 主要职责 | 不承担的职责 |
| --- | --- | --- |
| `core` | 实体、关系、身份与生命周期模型 | 启动外部测试、调用具体 Agent |
| `parsers` | Markdown/YAML/代码解析与来源定位 | 批准设计、裁决语义合理性 |
| `graph` | 索引构建、查询和双向影响传播 | 权限批准、修改权威设计 |
| `context` | 分级检索、排序、上下文装配与新鲜度检查 | 把推断提升为事实 |
| `design` | 设计、契约及评审记录的管理 | 代替外部审批者授权 |
| `verification` | 测试、契约、架构检查及证据管理 | 修改业务实现使检查通过 |
| `governance` | Policy、权限、工作流和门禁决策 | 以 Prompt 替代实际权限控制 |
| `cli` | 参数、调用编排、退出状态与结果输出 | 隐藏业务规则 |
| adapters | 文件系统、Git、CI、Agent 与产物存储适配 | 在宿主侧另建一套实体语义 |

Verification Engine（VE）归入 `verification`；Agent Governance（AG）归入 `governance` 和 Agent adapter；KG 由 `core/parsers/graph/context` 支撑。EPE 提供统一编排入口。

## 2. 依赖原则

核心模型不依赖 CLI、Agent SDK 或具体基础设施。解析器和图能力依赖核心抽象；设计、验证与治理通过明确定义的查询和存储接口协作；CLI 作为组合入口装配具体实现。

初期允许同进程调用，但禁止双向模块循环。外部进程执行、Git 与 CI 访问封装到适配器。将“读取事实”“计算决策”“执行副作用”分开，保证门禁决策可测试，外部工具可替换。

## 3. 主要数据流

1. Parsers 读取权威工件，输出实体、关系、诊断和来源。
2. Registry 校验 ID 与引用；Graph 生成带输入指纹的索引。
3. Context Resolver 根据任务与图提供相关事实和不确定项。
4. Design Manager 更新设计与契约，Review Manager 关联授权记录和设计版本。
5. Governance 结合任务、风险、设计版本和策略计算执行许可。
6. Verification 执行允许的检查，Evidence Manager 保存真实结果。
7. Gate Manager 判断质量门禁，Knowledge Synchronizer 重建受影响索引。

## 4. Agent 集成协议

建议工具操作为 `create_design`、`validate_design`、`request_approval`、`start_implementation`、`verify`、`finalize`。这些名称是目标接口，尚不可调用。

请求携带 Task / ChangeSet ID、调用者身份、目标实体、期望版本、写入范围和操作参数。返回决策、原因、诊断、关联 Evidence 与可执行下一步。客户端的 `approved: true` 不能直接改变服务端审批状态。

`start_implementation` 检查设计适用性、审批版本、风险权限和范围冲突；`finalize` 检查验证结果、证据新鲜度、映射和架构规则。读取检查不授予写权限。

Hermes、Codex CLI 和 Claude Code 适配器复用同一协议。只有当所有写入或合并路径受宿主权限、沙箱或 CI 控制时才能声称强制执行；可被绕过的本地 CLI 和 Git Hook 只能作为辅助检查。

## 5. 技术选择

| 能力 | 首选方案 | 引入条件 |
| --- | --- | --- |
| 文档与元数据 | Markdown、YAML | 首版 |
| 模型与结构校验 | Pydantic / JSON Schema | Schema 冻结后 |
| Python 解析 | AST | 首版 |
| 多语言解析 | Tree-sitter | 出现多语言需求后 |
| 图分析 | 内存图、NetworkX、JSON 索引 | 首版按复杂度选用 |
| 检索 | ID、图、关键词；后续 BM25 / 向量 | 按规模增量引入 |
| 测试与架构 | Pytest、Import Linter / 自定义规则 | 随实现建立 |
| API / 跨服务契约 | JSON Schema / OpenAPI、Pact | 存在相应接口时 |
| 自动化 | Git、CI；Hook 辅助 | MVP 集成阶段 |

Pact 面向消费者与提供者交互，不要求所有内部类契约都采用 Pact。避免为满足技术清单引入无使用场景的基础设施。
