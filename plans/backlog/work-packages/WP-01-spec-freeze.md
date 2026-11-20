# WP-01：冻结规范、机器契约和样例

**状态：** planned · **里程碑：** M0 / V0.1 · **实施：** not_started  
**负责模块：** 全部；core / governance / design 牵头  
**上游：** PRD、SPEC、架构、9 模块草案 · **下游：** 全部实现 WP

## 1. 目标

把分散在 PRD/SPEC/模块中的字段、关系、状态、错误与结果模型落实为可校验机器契约与模板，关闭实现前必须决策项，使后续 WP 不再靠猜测公共协议推进。

## 2. 任务分解

| 子任务 | 内容 | 产出类型 |
| --- | --- | --- |
| T1 | 逐项核对 PRD→SPEC→模块→AC 一致性；列出冲突与缺口 | 决策日志 / ADR 候选 |
| T2 | 冻结实体分型 Schema、ID 前缀、未知字段策略 | `engineering/schemas/` |
| T3 | 冻结关系端点矩阵、基数、环约束与 origin/verified | Relation Schema |
| T4 | 冻结 Task / ChangeSet / Approval / Evidence / Policy / Workflow | 治理 Schema |
| T5 | 冻结指纹范围、manifest 序列化、Evidence 有效性规则 | 规范章节 + Schema |
| T6 | 冻结 CLI 结果模型、退出码优先级、诊断 code 命名空间 | CLI / Result Schema |
| T7 | 冻结快照 generation、锁、恢复、审计路径与保留期 | 存储约定 |
| T8 | 编写文档模板与正反例夹具 | templates + fixtures |
| T9 | 用校验器跑通正反例；未决项标 blocking/deferred | 验收记录（手工亦可） |

## 3. 拟议交付路径

```text
engineering/
  schemas/
    entity/
      common.schema.json
      design-entities.schema.json      # Intent/Spec/Arch/Module/Component/Class/ADR
      implementation-entities.schema.json  # SRC-/SYM- 等
      execution-entities.schema.json  # Task/ChangeSet/RUN-
      evidence-entities.schema.json
    relation.schema.json
    approval.schema.json
    evidence-record.schema.json
    policy.schema.json
    workflow.schema.json
    cli-result.schema.json
    source-location.schema.json
    input-manifest.schema.json
  policies/
    documentation.yaml
    architecture.yaml
    verification.yaml
    risk-gates.yaml
  workflows/
    feature.yaml
    bugfix.yaml
    refactor.yaml
    exploration.yaml
docs/standards/templates/
  module.md
  component.md
  class.md
  contract.md
  adr.md
  task.md
  change-set.md
  evidence.md
tests/fixtures/schema_cases/
  valid/
  invalid/
```

路径可在 T1 后微调，但同类工件不得拆散到多套冲突目录。审计记录（Approval、Evidence、Task）权威位置不得落在 `.engineering/`。

## 4. 必须决策（关闭前不可进入依赖实现）

| ID | 议题 | 建议默认 | 备选 | 影响 WP |
| --- | --- | --- | --- | --- |
| D-01 | 审批可信配置位置 | `engineering/policies/trust.yaml` + CI OIDC/环境身份；仓库内 reviewer 名不可自证 | 外部密钥托管 | WP-06/07/14 |
| D-02 | 批准记录存储 | `reports/approvals/` 或 `docs/...` 外的独立审计目录，Git 跟踪 | 仅 CI artifact | WP-06 |
| D-03 | 设计指纹范围 | 设计正文规范化字节 + 显式引用契约内容摘要；不含 Frontmatter 中派生显示状态 | 含全部 Frontmatter | WP-06/07 |
| D-04 | 批准操作是否改设计文件 | **否**；只追加 Approval 记录；显示状态由计算得出 | 写回 Frontmatter | WP-06 |
| D-05 | 撤销顺序 | 新记录 `revoked` 引用原 approval id；有效集按记录序列，不靠客户端时钟 | 物理删除 | WP-06/07 |
| D-06 | 输入 manifest 范围 | 保守：纳管 docs/engineering/src/tests + 有效验证配置；排除 `.engineering/`、`reports/`、venv | 依赖闭包缩小（后置） | WP-08 |
| D-07 | Evidence 保留期 | 默认保留全部记录与缺失标记；产物可按策略清理但记录保留 | 仅保留 N 天产物 | WP-08/11 |
| D-08 | 快照 generation | 单调整数或 ULID；写 `generation/` 临时树后原子换 `current` 指针 | 多文件无指针原地替换（禁止） | WP-05/10 |
| D-09 | 写锁 | `.engineering/write.lock` 租约 + 持有者/到期；冲突退出码 5 | 无锁乐观覆盖（禁止） | WP-05/10 |
| D-10 | 锁恢复 | 过期可强制夺取并记审计；未过期冲突必须失败 | 任意覆盖 | WP-10 |
| D-11 | 混合故障退出码 | 优先 3（故障）> 1（阻断）> 2/4/5；诊断全保留 | 按抛错顺序 | WP-09 |
| D-12 | 诊断 code 空间 | `MODULE_SNAKE` 稳定枚举，消息可改、code 不复用 | 自由字符串 | 全模块 |
| D-13 | ID 前缀完整表 | 沿用架构表 + `SRC-`/`SYM-`/`RUN-`/`APPROVAL-`；内部定位键单独前缀或命名空间 | 路径哈希当工程 ID（禁止） | WP-02/03 |
| D-14 | Schema 未知字段 | 默认拒绝；扩展仅 `extensions` | 宽松忽略 | WP-02 |
| D-15 | High 风险在可信源未就绪时 | **阻断**，不可确认 | 降级为 Medium 警告（禁止默认） | WP-06/07 |

每项决策结果写入短 ADR 或 `plans/...` 决策附录，并回写 SPEC 对应章节；不得只留在聊天记录。

## 5. 正反例最低集

**正例：** 最小 Module+Class+Contract+Task+ChangeSet；合法 `realizes`；合法 Low 风险自动审核策略；完整 Evidence 记录字段。

**反例（必须失败）：**

1. 重复实体 ID（内容相同也冲突）
2. YAML 重复键
3. 未知顶层字段
4. 非法关系端点 / 自 contains / supersedes 环
5. `verified: true` 缺验证元数据
6. Approval 缺内容指纹或身份来源
7. Evidence 缺实际参数数组或用字符串命令代替参数数组
8. CLI result 缺 `schema_version` / `status`
9. 状态枚举拼写错误
10. Policy 缺必需规则却声称可求值

## 6. 验收映射

| 检查 | 关联 |
| --- | --- |
| Schema 正反例可自动或脚本校验 | SPEC §3、§11；路线图 §4 |
| 关键歧义均有 D-xx 结论或显式 deferred | 总计划 WP-01 |
| 批准不导致自身设计指纹变化（契约层可描述） | D-03/D-04 |
| 运行结果不进入源 manifest（契约层可描述） | D-06 |
| PRD↔SPEC↔模块无未记录冲突 | T1 |

本 WP **不要求** 引擎代码；可用 JSON Schema 校验器 + 手工评审关闭。无代码不等于无验收记录。

## 7. 完成门槛

- [ ] T1–T9 产出已入库且互相引用一致
- [ ] D-01 至 D-15 全部 closed 或 deferred（deferred 不得被下游实现偷偷假设）
- [ ] 至少一轮适用评审记录（人类），文档仍标 `design_status: draft` 直至正式批准流程建立
- [ ] 下游 WP 可引用具体 Schema 文件路径，不再引用“见架构散文”

## 8. 风险

规格相互冲突、审批可自证、指纹过宽导致永远 stale、指纹过窄导致漏检。冲突一律先改规格再实现。
