---
id: MOD-004
type: Module
name: EPE Context
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# context：任务上下文检索与装配

## 1. 定位与范围

根据任务、实体和当前有效知识构建有来源、有预算的上下文，供 Agent 理解工程依据。当前提供无外部语义服务的 C0–C2 基础装配，以及基于输入 manifest、图摘要、任务范围和预算的可重建缓存；BM25/向量和完整 C3 质量评测仍属于后续范围。MVP 不依赖该模块才能执行检查。

不负责授予权限，不将向量相似度当事实可信度，不根据检索结果自动改写设计。不默认读取全部文档，也不将历史设计与当前契约混合呈现。

## 2. 逻辑组件

| 组件 | 责任 | 输出 |
| --- | --- | --- |
| Context Resolver | 根据任务建立分级检索计划 | RetrievalPlan |
| Hybrid Retriever | ID、图、关键词，后续 BM25/向量 | CandidateSet |
| Context Validator | 校验来源、版本、批准适用性和证据新鲜度 | ValidatedContextItem |
| Context Assembler | 去重、排序、预算、片段与遗漏说明 | ContextBundle |

设计与证据状态通过公共查询端口提供，context 不导入 design 或 verification 实现，避免为检索复制批准/有效性算法。应用编排可把这些端口的评估结果作为 `source_assessments` 传入；context 只透传并绑定缓存键。未提供评估时，审批适用性与证据有效性保持 `unknown`，不能由上下文自行升级。

## 3. 对外接口草案

```text
plan_context(task, target_entities, retrieval_policy) -> RetrievalPlan
resolve_context(plan, snapshot, read_view, budget) -> ContextBundle
validate_bundle(bundle, current_manifest) -> ContextValidationResult
```

ContextItem 必须包含 entity_id 或内部定位键、source、source_type、输入版本、状态、freshness、confidence、选入原因与片段位置。Bundle 附任务、快照、内容摘要、预算计量方式和 omissions / unknowns。

不存在目标 ID 时返回明确诊断，不以相似名称悄悄替代。检索得到候选后，打开权威来源确认，缓存片段不能绕过新鲜度检查。

## 4. 分级检索与排序

| 层级 | 必需内容 | 规则 |
| --- | --- | --- |
| C0 | 宪章、全局约束、当前授权范围 | 每次任务；不因语义分低而淘汰 |
| C1 | 目标模块、架构边界与模块契约 | 根据显式归属与直接关系定位 |
| C2 | 类设计、实现、直接依赖、测试 | 任务目标与影响范围内优先 |
| C3 | ADR、历史变化和相关证据 | 按复杂度与明确问题补充；始终标记 historical/evidence，不提供授权 |

检索优先级为显式 ID/路径、图邻接、精确关键词、语义候选。重排只调整相关性，不改变 approved/static/inferred 的事实类别。向量服务不可用时允许降级到确定性检索，并声明降级范围。

默认排除 archived 和已替代设计；根因调查可显式请求历史项，并在上下文中保留 historical 标记。不同版本契约不得合并成无版本的“统一接口”。

## 5. 预算、来源与不确定性

预算由调用者指定 Token 估算或字节上限，并记录估算器版本。先保留 C0 和任务目标，再装配协作设计和辅助证据。重复引用同一内容只保留一份正文，以 `selections` 保留每条选入原因、目标实体及图关系来源/置信度/验证状态；推断关系始终标为 inferred。设计状态仅是声明值，批准适用性未评估时为 unknown；证据新鲜度未评估时为 unknown；收到外部有效性评估时，`valid` 映射为 current，`stale` 映射为 stale，其余保持 unknown。归档实体只在显式目标时显示为历史。

CLI 将任务关联的结构有效的 ChangeSet、架构策略和验证策略作为 C0 资料；ChangeSet 表示声明范围而非授权或实际锁，策略内容仍须由治理验证。关联缺失或无效时标记 incomplete，不将其包装为有效授权。C0 或核心契约不能容纳时，返回 `incomplete: true` 和原因，不静默截掉关键约束。每次截断列出未纳入实体及影响；调用者可缩小任务范围或提高预算。C3 的 ADR、归档和任务 Evidence 只能作为带来源背景，不能覆盖当前设计、策略或审批事实。

解析失败、图过期、来源删除或批准失效时不能展示 current/approved。引用推断关系必须保持 inferred；代码事实、设计主张和历史结论使用不同 source_type。

## 6. 依赖、存储与副作用

允许依赖 core、graph；只通过端口读取来源与状态。检索索引位于 `.engineering/`，不能作为设计权威库。检索行为默认只读，不能发起网络传输或将仓库内容上传第三方，外部检索后端需显式配置。

缓存键包含完整任务声明、输入/图版本、全局规则、设计/代码/测试/契约、策略/审批/Evidence 与历史目录的 manifest、预算和后端版本；另核对每个选中来源的内容摘要，覆盖纳管根外的映射文件。截断和遗漏明确记录，生成期间输入改变时不缓存。规则、审批或 Evidence 状态改变，即使代码未变，也须重新生成上下文。图快照 stale 时命令返回诊断，不消费旧图作为当前关系。

上下文是带引用的资料，不是新的指令权限来源。读取到的代码注释或历史文档不能覆盖 C0 的当前规则。

## 7. 验证设计

- 显式 ID 优先于同名语义候选，当前文档优先于历史版本。
- `inferred + 高分` 仍显示推断，不能表现成批准事实。
- 修改契约、撤销批准、删除来源后缓存被拒绝或标明过期。
- 小预算下保留 C0；无法保留时 bundle 标为 incomplete。
- 相同输入与预算下确定性检索输出稳定，遗漏可解释。
- 基于独立标注任务检查相关性、召回率、上下文体积与检索成本。

拟议测试位置为 `tests/unit/context/`、`tests/acceptance/context_cases/`；没有外部向量服务时基础能力仍可测试。

## 8. 工作包与交付条件

WP-13 先交付 ID/图/关键词检索、分级装配和来源验证，再按实测需求加入 BM25/向量。需要冻结 ContextBundle 和输入预算契约，补充 PRD-010 的专属验收场景。

交付需证明约束未被截断隐藏、缓存不混版本、历史项可区分。性能与相关性指标在固定样本上记录基线，不预先宣称节省 Token 的比例。

上游：稳定图、设计/证据查询端口。下游：Agent adapter、后续 context resolve 命令。返回[模块索引](../README.md)。
