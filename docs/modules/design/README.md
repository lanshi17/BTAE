---
id: MOD-005
type: Module
name: EPE Design
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# design：设计、契约与评审管理

## 1. 定位与范围

维护设计内容、机器契约与评审依据，回答“设计是否完整”和“这份批准是否仍适用于当前设计”。对应 PRD-005，支撑 AC-05、AC-12。

MVP 提供设计/契约校验、按模板安全生成设计、批准记录适用性检查和签名记录导入。权限授予由 governance 判定，身份真实性由可信 adapter 提供；design 本身不授予审批者权限。

## 2. 逻辑组件

| 组件 | 职责 |
| --- | --- |
| Design Manager | 定位实体设计，检查职责、接口、状态与验收关联 |
| Contract Manager | 校验契约格式、引用和确定性结构约束 |
| Review Manager | 绑定评审记录、内容版本和可信身份事实 |
| Design Fingerprint | 计算设计内容及引用契约的适用版本 |

Mapping Validator 不在本模块：它检查实际实现，由 verification 承担。设计声称某方法存在只构成设计要求，不构成实现事实。

## 3. 对外接口草案

```text
validate_design(entity_id, registry, document_view, requirements) -> DesignCheckResult
validate_contract(contract_id, contract_view, validator_options) -> ContractCheckResult
describe_design_revision(entity_id, design_inputs) -> DesignRevision
assess_approval(revision, approval_record, trusted_identity_fact) -> ApprovalAssessment
prepare_approval_record(revision, review_decision) -> ApprovalRecordCandidate
```

DesignCheckResult 附缺失章节/字段、验收关联、契约状态和输入指纹。ApprovalAssessment 区分匹配、过期、撤销、来源未知和内容错误，但不直接返回调用者有权批准。

## 4. 设计与契约检查

模块设计检查边界、公共服务与依赖；组件检查协作与故障责任；核心类检查职责/非职责、接口、状态、不变量和测试映射。检查模板要求由版本化配置提供，不在代码中写死每个章节标题。

JSON Schema 契约进行语法和引用校验，接口契约使用受支持的格式校验器。缺少对应校验器时返回 unsupported / unknown，不以文件存在代表契约通过。

行为条件可以映射到测试，但自然语言“满足不变量”的自动判断属于 D3 辅助项。MVP 不执行 Markdown 内嵌代码、任意表达式或 LLM 自评来批准设计。

## 5. 指纹、评审与状态

1. 定位当前设计正文、声明元数据、引用契约及其指纹。
2. 用规范化清单形成 DesignRevision；记录算法版本，防止算法变化后旧批准被误用。
3. 读取批准记录，核对 entity_id、revision、决策、撤销关系和可信身份来源。
4. 输出批准适用事实，交由 governance 结合风险与权限完成门禁判断。
5. 通过授权后追加不可覆盖的记录；禁止直接改 Frontmatter 获得批准。

批准记录与派生状态不写入所批准的设计内容，避免批准操作使自己的设计指纹变化。原始声明元数据参与指纹；展示的 effective status 单独计算，不自动回写正文。任何正文或契约变化均需重新评估批准。

当前 `epe-design-revision-v3` 使用设计源文件原始字节摘要、完整原始声明元数据（包括 extensions）及引用契约的原始字节摘要；设计源不能是符号链接，路径必须留在仓库根内；读取失败或越界时不能生成有效版本。旧算法的批准不会自动迁移，需按当前 revision 重新签署。

审批适配器使用 OpenSSH Ed25519 签名，签名内容是除 `signature` 字段外的 UTF-8 JSON（键排序、无多余空格、无结尾换行），namespace 为 `epe-approval`。维护者须在受保护的 `engineering/epe.yaml` 中配置 `approval_trust.identities`，每个身份包含 `public_key`、`kind: human|service` 和 `risk_scope`。导入与完成检查均重新验签；高风险必须匹配受信 human 和风险范围，中风险还须与 ChangeSet owner 不同。受保护配置和私钥属于信任根，普通仓库文件本身不能保证其真实性。

撤销使用经授权签名、决策为 `revoked` 的独立记录，并通过 `supersedes` 引用同实体和同 revision 的批准；撤销者的配置风险范围和撤销记录必须覆盖被撤销批准的风险。失效或不可验证记录不会获得授权。审批记录仍可被仓库写入者删除，实际防删除和审核依赖宿主权限与 CI；当前未实现不可变远程审计服务。

审批导入使用本地 EPE 写锁；审批文件与审计事件分别持久化。签名批准只有在完整性校验通过的审计链中存在绑定审批对象完整摘要的 `approval_committed` 事件时才可用于门禁。审计写入失败时，同一签名记录可显式重试补录；未经提交的有效签名撤销仍保守生效。旧版无内容摘要的事件不能自动作为提交，可用原签名记录重试。`epe audit verify` 检查现存链的结构和摘要；本地链无法检测整个链或尾部被删除，也不提供跨文件事务或外部防篡改保证。

同一记录冲突、撤销与批准先后关系需通过显式引用和序列解决，不能依赖客户端时间戳排序决定有效性。该记录格式在 WP-01 冻结。

## 6. 依赖、持久化与失败

只允许依赖 core。文档、契约与记录读取通过端口完成，可信身份来自 adapter 注入值，调用者的 `role: human` 不产生信任事实。

设计与契约仍存原有权威位置；审批记录使用独立审计存储。路径、保留策略与可信来源配置由 WP-01/WP-06 冻结，不放入 `.engineering/` 以免缓存清理丢失授权依据。

缺设计或契约不完整是阻断诊断；不可读或无法解析是故障；身份来源不足是无法确认批准，不得默认通过。重复导入同一不可变记录可返回已存在，ID 相同内容不同必须冲突。

## 7. 验证设计

- 缺职责/验收映射、契约引用缺失产生可定位诊断。
- 有效批准匹配当前内容；改正文、元数据或引用契约后失效。
- 仅将 Frontmatter 改为 approved 或自称 reviewer，不能满足门禁。
- 导入批准本身不改变 DesignRevision；撤销后不能继续使用原记录。
- 不支持的契约格式明确报告；低风险自动检查与高风险人工批准保留不同来源。
- 构造失败记录和同 ID 不同内容的重复导入，原记录保持完整。

当前设计生成、契约 Schema 和 SSH 签名审批均有 CLI/集成覆盖；扩展测试仍位于 `tests/unit/` 和 `tests/integration/`。

## 8. 工作包与交付条件

WP-01 补齐各层模板与批准 Schema；WP-06 实现设计/契约校验和批准适用性。与 governance 联合完成 AC-05：design 提供内容事实，governance 负责允许或阻断。

交付需包含 DesignRevision 契约、可信记录导入流程、撤销与内容变化测试。核心设计管理类需独立类文档；不把本模块的设计草案登记成已批准实现。

上游：core、文档读取与可信身份端口。下游：governance、context、CLI。返回[模块索引](../README.md)。
