# 工程知识模型与双向追溯

状态：v0.1 设计草案。以下字段是 Schema 设计依据；对应 JSON Schema 已位于 `engineering/schemas/`，完整运行时校验仍在演进。

## 1. 统一实体

| 类别 | 实体 |
| --- | --- |
| Design | Intent、Spec、Architecture、Module、Component、Class、Contract、ADR |
| Implementation | Source File、Symbol、Function、API、Data Model、Configuration |
| Execution | Task、Agent Run、Pull Request、ChangeSet |
| Evidence | Test、Evaluation、Build、Benchmark、Verification Report、Evidence |

实体 ID 稳定且不可复用，名称与路径变化不改变逻辑身份。标准前缀包括 `PROJ-`、`INTENT-`、`SPEC-`、`ARCH-`、`MOD-`、`COMP-`、`CLASS-`、`CONTRACT-`、`TASK-`、`CHANGE-`、`TEST-`、`EVIDENCE-`、`ADR-`；其余类型前缀在 Schema 中统一定义后启用。

核心类一类一份设计文档，文档描述职责、非职责、协作、不变量、错误与状态模型；机器契约独立存放。允许一个实体映射多个文件，同一文件包含多个实体。映射应提供路径和可解析符号定位，避免仅以文件名判断对应关系。

```yaml
id: CLASS-AGENT-001
name: AgentManager
design_status: draft
implementation_status: not_started
verification_status: pending
implementation:
  - path: src/agent/manager.py
    symbol: AgentManager
  - path: src/agent/lifecycle.py
    symbol: AgentLifecycle
verification:
  - test_id: TEST-AGENT-001
    path: tests/unit/agent/test_manager.py
contracts:
  - CONTRACT-AGENT-001
```

这是目标映射示例，所列文件不是当前仓库实现。

## 2. 关系语义

| 关系 | 方向与含义 | 示例 |
| --- | --- | --- |
| `contains` | 容器 → 成员 | Module → Class |
| `realizes` | 逻辑设计实体 → 实现定位实体 | Class → Source / Symbol |
| `specifies` | 规格 → 被规定对象 | Spec → Component |
| `depends_on` | 使用者 → 被依赖对象 | Class → Class |
| `conforms_to` | 实现对象 → 约束契约 | Symbol → Contract |
| `verified_by` | 被验证对象 → 验证定义 | Class / Contract → Test |
| `evidenced_by` | 变更或验证对象 → 执行证据 | ChangeSet → Evidence |
| `constrained_by` | 受约束对象 → 约束依据 | Module → ADR |
| `supersedes` | 新实体 → 被替代实体 | New Design → Old Design |
| `affects` | 变更 → 受影响实体 | ChangeSet → Entity |

`realizes` 沿用初始方案的“设计到实现映射”方向，不能按日常英语自行反转。各类型合法端点、基数与循环约束需在关系 Schema 中落实。反向追溯由索引生成，不要求人工维护成对反向边。

```yaml
from: CLASS-AGENT-001
to: SRC-AGENT-001
relation: realizes
confidence: 1.0
origin:
  type: explicit
  source: docs/classes/agent/manager.md
verified: false
```

来源类型区分 `explicit/static/inferred`，且每条关系必须记录非空 `origin.source`；验证状态独立记录 `verifier`、`method`、UTC 时间与依据 `version`。`verified=true` 必须提供完整验证元数据，未验证关系不能携带矛盾的 verification 对象。显式声明或高 confidence 不自动等同于真实、已批准或已验证。

## 3. 权威来源与派生数据

| 信息 | 权威来源 | 派生用途 |
| --- | --- | --- |
| 设计意图与职责 | Markdown | 上下文与设计索引 |
| 结构化规格 | YAML / JSON Schema | 契约校验与门禁 |
| API / 消息契约 | OpenAPI / Protobuf 等 | 接口与消费者验证 |
| 实际实现 | Git 管理的代码 | AST、符号与依赖索引 |
| 测试定义 | 测试仓库文件 | 验证映射 |
| 执行结果 | CI Artifact 或本地可定位产物 | Evidence 与结果索引 |
| 声明关系 | 工件元数据 | 关系图 |
| 观测关系 | 解析或运行采集结果及来源 | 发现架构与影响候选 |
| 运行状态 | 数据库与 Observability | 运行反馈 |

`.engineering/` 中 JSON、BM25 和向量索引均是可重建视图。更新索引不得反向覆盖设计意图，也不能把发现架构直接提升为预期架构。

首版使用 Python 内存图与 JSON 索引；NetworkX 可用于图算法。图数据库仅在跨仓库规模和查询复杂度需要时引入。生成过程应检测重复 ID、悬空边、解析失败，避免静默丢弃错误工件。

## 4. 独立生命周期

| 维度 | 初始状态集合 | 约束 |
| --- | --- | --- |
| Design | `draft/reviewed/approved` | 审批绑定设计版本或指纹 |
| Implementation | `not_started/in_progress/implemented` | 已实现不等于验证通过 |
| Verification | `pending/passed/failed` | 表示特定版本的执行结果 |
| Evidence validity | `valid/stale/invalid/unknown` | 表示当前能否使用该证据 |

归档、撤销、停用等状态在正式 Schema 冻结时补充。设计变更需重新评估审批，代码或契约变更需重新计算证据适用性。`approved + implemented + failed` 是合法组合，不能用单一状态掩盖失败。

## 5. Evidence 模型

Evidence 记录一次执行事实，不能只存 `passed: true`。至少包含 ID、目标实体、关联 ChangeSet、实际命令、工作目录、开始和结束时间、退出码、测试结果、环境、产物位置及完整性摘要。

版本来源至少记录提交号（存在时）、工作树是否有修改、源代码指纹、契约指纹、测试指纹、验证配置和相关依赖。无提交时显式记录未提交状态；只有提交号不足以描述脏工作树。

- `valid`：相关输入与验证环境要求匹配，证据完整且结果可解释。
- `stale`：相关输入变化或超出策略有效期，需要重跑。
- `invalid`：证据损坏、不可信或不满足执行要求。
- `unknown`：输入、环境或影响范围不足以判断。

证据有效不代表测试通过；失败结果也可以是当前有效的诊断证据。门禁同时判断执行结果与证据有效性。历史证据保留，不通过删除失败记录制造完成状态。

## 6. 五维一致性与漂移

| 关系 | 验证内容 |
| --- | --- |
| Design ↔ Contract | 职责、不变量与接口是否一致 |
| Contract ↔ Code | 签名、结构与可执行约束是否符合 |
| Code ↔ Test | 实际行为是否得到相关测试 |
| Design ↔ Test | 需求与不变量是否有验证条件 |
| Architecture ↔ Code | 边界、依赖和公共接口是否符合 |

分级检测：D0 用 AST 检查文件和符号；D1 用签名和 Schema 检查接口；D2 用契约与测试检查行为；D3 用 LLM、依赖图与评审识别职责和架构偏移。每一级报告其覆盖范围，低层通过不推导高层通过。

## 7. 双向增量影响分析

代码变化定位 Source / Symbol 后追溯到设计、契约、消费者、测试与 Evidence；设计变化沿实现映射传播到代码、测试与依赖者。`depends_on` 的消费者影响需要逆向遍历，不能对所有边统一沿同一方向无限扩散。

影响结果区分确定影响与候选影响，保存传播路径、原因、来源和可信度。首版规则传播采用保守策略；解析盲区提示扩大检查范围。索引记录输入指纹，版本不匹配时重建或声明未知，不返回伪精确结论。
