---
id: MOD-001
type: Module
name: EPE Core
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# core：工程领域模型与注册

## 1. 定位与范围

提供工程实体的统一身份、关系语义、状态与跨模块契约，是其他模块共同依赖的领域基础。对应 PRD-002、PRD-005、PRD-007、PRD-009，支撑 AC-02、AC-05、AC-07、AC-11。

MVP 包括类型模型、注册快照、关系校验、状态迁移和必要端口；不启动测试、不解析 Markdown、不读写仓库、不判断某人是否具有实际权限。图遍历、内容评审与门禁策略不属于 core。

## 2. 逻辑组件

| 组件 | 输入 | 输出与不变量 |
| --- | --- | --- |
| Entity Registry | 已解析的实体候选、已有身份记录 | 唯一 ID 的不可变快照；冲突不覆盖 |
| Relationship Manager | 边候选、实体快照、关系规则 | 端点/类型/基数诊断；保留来源 |
| Lifecycle Manager | 当前状态、事件、绑定版本 | 合法迁移或拒绝原因；不直接写存储 |
| Contract Models | Schema 定义、原始字段 | 类型化值对象；拒绝未知字段和非法枚举 |
| Port Definitions | 应用所需最小外部能力 | Repository、ArtifactStore、Git、Process、Clock、Identity 等协议 |

端口按实际用例增加，不创建通用插件系统。Pydantic 可用于数据校验，但业务模型不依赖 CLI、Git SDK 或 Agent SDK。

## 3. 对外接口草案

```text
register_batch(candidates, relations, previous_snapshot) -> RegistryBuildResult
get_entity(snapshot, entity_id) -> Entity | Diagnostic
validate_relation(relation, snapshot, relation_rules) -> CheckResult
transition(subject, event, expected_revision) -> TransitionResult
canonical_manifest(entries) -> InputManifest
```

`RegistryBuildResult` 包含快照、诊断、输入版本和是否完整。批量注册先收集实体，再验证引用，允许文件读取顺序不同；重复 ID 即使内容相同也报冲突，防止多个权威来源悄悄合并。

Entity、Relation、Task、ChangeSet、Approval、Evidence 等类型按 SPEC 分型校验。Evidence 的事实模型在此定义，有效性算法由 verification 实现；GateDecision 的数据结构在此定义，规则由 governance 实现。

## 4. 身份与状态规则

1. ID 创建后不可复用；名称与路径是可变定位信息。归档保留身份与替代关系。
2. 自动发现但未注册的符号只有内部定位键，不能自动获得已批准设计实体身份。
3. `realizes` 固定为设计到实现；反向关系是查询视图。禁止自包含和包含环，依赖环交由架构策略处理。
4. `origin` 与 `verified` 独立；已验证边必须带 `verifier`、`method`、UTC 时间戳和依据 `version`，否则关系批次不能发布。
5. 设计、实现、验证和证据有效性独立。状态声明不代替实际审批或验证事实。
6. `expected_revision` 不匹配返回冲突，禁止用旧状态覆盖新状态。设计变化产生失效事件，历史记录保留。

迁移函数只返回新状态和事件，由调用方通过端口持久化；必须提供 expected revision，旧 revision 不得覆盖新状态。没有有效配置与事实时，不在 core 内默认补齐 `approved` 或 `passed`。

## 5. 依赖、存储与一致性

内部依赖为空；其他模块通过公共模型与端口引用 core。输入快照只读，任何变更生成新 revision；跨模块不得持有可变注册字典并原地更新。

Registry 是知识组织能力，不是第二份文档权威库。索引可重建；ID 的归档与不可复用记录必须随权威元数据保留，不能在清空缓存时遗失。具体持久化格式在 WP-01 冻结。

manifest 的规范化序列化必须集中定义：路径排序、UTF-8、稳定 JSON、SHA-256，不能由模块各自实现不同摘要。文件读取和字节摘要采集通过 adapters 完成，core 负责确定性组合。

## 6. 诊断与恢复

| 情况 | 行为 |
| --- | --- |
| 重复 ID / 未知类型 | 拒绝当前注册批次发布，定位所有冲突源 |
| 悬空关系 / 非法端点 | 返回关系诊断，不静默丢边 |
| 非法状态事件 | 保留当前状态，返回迁移拒绝 |
| 旧 revision 写入 | 返回冲突，要求重读快照 |
| 缺来源或验证依据 | 不允许生成“已验证”关系 |

诊断应带实体和路径；敏感内容不进入通用错误字符串。批次失败不破坏原快照。

## 7. 验证设计

- 同一批实体随机改变文件读取顺序，注册结果和关系内容一致。
- 两份文档声明同一 ID，明确报错；符号移动仅改变定位，实体 ID 保留。
- 正反端点混用、非法 confidence、自包含/替代环分别被拒绝。
- `approved + implemented + failed` 可表示；缺审批记录不能据此授权。
- 旧 revision 迁移不能覆盖新 revision；归档后新实体不能复用原 ID。
- 多字节路径与不同字典插入顺序生成相同规范化 manifest。

当前基础测试位于 `tests/unit/test_core.py`；契约和完整迁移场景仍待扩展。

## 8. 工作包与交付条件

WP-01 冻结分型 Schema、前缀、关系矩阵及状态事件；WP-02 实现模型、注册与必要端口。实现前为注册、关系和生命周期核心类补齐独立设计。

交付必须包括模型、Schema 一致性检查、上述正反例及迁移文档。后续若更改公共字段，提供 schema_version 迁移，不允许单个消费者私自接受新字段。

上游：SPEC 和 Schema 草案。下游：其余所有模块。返回[模块索引](../README.md)。
