---
id: MOD-007
type: Module
name: EPE Governance
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# governance：策略、权限与门禁

## 1. 定位与范围

对任务能否开始实现、是否允许执行检查、是否可以完成给出可解释决策，是治理平面的规则中心。对应 PRD-005、PRD-008、PRD-009、PRD-011，支撑 AC-05、AC-09、AC-11、AC-12。

当前实现任务记录校验、四类任务的激活/完成/中止状态迁移、风险与权限、设计/完成门禁、ChangeSet 基线和已知写入冲突报告；任务激活会读取并 Schema 校验对应 Workflow 的 `required` 字段，配置漂移时 fail closed。完整多 Agent 协调仍需宿主集成。权限系统只能控制经集成的执行路径，不把 Prompt 视为文件系统隔离。

Task / ChangeSet 的顶层字段默认拒绝未知项，revision 必须是正整数；四类工作流的专属前置资料由状态迁移校验。`epe policy validate` 使用对应 JSON Schema 校验架构/验证策略和四类 Workflow 文件，并执行验证检查项的非空 ID、argv、timeout 与解析器语义校验；未知字段、空必需检查或符号链接策略属于故障。策略字段未知、类型错误或 Schema 文件不可用时返回故障，不能由业务命令各自宽松解释。

## 2. 逻辑组件

| 组件 | 职责 |
| --- | --- |
| Policy Engine | 加载后的策略语义校验、适用范围和有效规则求值 |
| Permission Manager | 结合可信身份、操作、风险与范围计算授权 |
| Workflow Engine | 校验任务类型、阶段依赖与状态迁移 |
| Gate Manager | 聚合检查事实，输出允许/阻断/故障及原因 |
| Scope Conflict Checker | 比较 ChangeSet 的受保护与允许范围，报告重叠 |

不自行解析代码、不启动测试、不计算设计正文指纹、不验证 Evidence 产物摘要。所需事实由 design、verification、Git 和 identity provider 通过共享值对象提供。

## 3. 对外接口草案

```text
validate_policy(policy_document, policy_schema) -> PolicyValidationResult
evaluate_permission(operation, trusted_identity, task, effective_policy) -> PermissionDecision
evaluate_gate(gate_kind, task, change_set, gate_facts, effective_policy) -> GateDecision
transition_task(task, event, expected_revision, gate_decision) -> TaskTransition
check_scope(actual_changes, write_scope, protected_scope) -> ScopeCheckResult
```

GateFacts 包含设计完整性、批准适用性、映射、架构、验证、Evidence、基线/当前版本与实际改动事实，每项附来源和输入版本。缺事实以 unknown 表达，不能填默认 true。

## 4. 策略与授权规则

全局工程约束优先于局部任务配置，受保护范围优先于允许写入范围；项目可收紧门禁，不能由任务自定义配置放宽高风险审核。风险由变更实体和公共边界推导，调用者建议只作候选。

Low 可采用配置的自动审核；Medium 需独立评审事实及自动检查；High 需明确的人类批准。独立性应核对 owner、reviewer 和身份来源，不仅比较显示名。已有授权仅在目标、操作、范围和设计版本仍匹配时复用。

Policy 本身的修改也应纳入变更与审核，不能修改规则后马上自证原违规已通过。首次初始化允许建立配置，但不产生 High 变更的通用授权。

## 5. 门禁算法

1. 验证策略、任务、ChangeSet 和事实模型是否完整，故障时返回 error。
2. 核对快照、设计、批准和验证事实的版本；旧事实标记 unknown/stale。
3. 根据操作和风险选择必需门禁，验证身份权限和实际范围。
4. 聚合规则：按检查、命令、版本、任务和 ChangeSet 匹配全部记录，按带时区的实际完成时间选最新，再判断 validity 与结果；最新记录为 fail、未执行或 stale/invalid/unknown 时不允许完成。匹配记录时间缺失、非法或缺少时区时无法可靠排序，保守阻断；同一时刻的最新记录必须全部满足条件。
5. 有效 warning 显示但不阻断；规则例外必须绑定有效 ADR、批准范围和期限。
6. 输出 decision、全部原因、输入版本和建议下一步，禁止只返回布尔值。

决策不永久缓存为执行许可。执行前和 finalize 前重新校验 expected_revision，避免批准后输入变化仍继续；强制防护还需宿主限制与 CI。

## 6. 工作流与并发

支持 feature/bugfix/refactor/exploration 的类型和状态迁移。Feature 要验收与设计；Bugfix 激活需要 reproduction；Refactor 激活需要 baseline_manifest；Exploration 激活需要 hypothesis。CLI 完成事件重新执行综合检查，不能信任调用者自报 `passed`；中止保留当前任务记录和 revision。

ChangeSet 生命周期通过 `changeset transition` 迁移：planned → active → completed，planned/active 可 aborted；每次迁移递增 revision；完成前要求关联 Task 为 active，并重新执行包含设计、架构、验证证据与范围的综合门禁；planned 或 aborted ChangeSet 不能满足 Task 完成门禁。生命周期字段不参与新基线声明摘要，避免合法状态迁移使自身基线失效；旧格式基线仅在原声明匹配时可只读比较，不自动迁移。Task 的内部执行阶段和 ChangeSet 状态分开定义，具体枚举在 Schema 冻结时落实。

范围检查包含新增、修改、删除、移动前后路径和符号链接解析结果。重叠声明只产生冲突事实，MVP 不声称给多个 Agent 上了实体锁。V1.0 引入锁时再定义租约、续期、恢复和依赖契约版本协调。

`epe changeset create --file PATH` 将当前仓库内容登记为基线并写入审计目录；完成门禁将当前路径和摘要与该基线比较，保护范围优先。基线摘要覆盖 ChangeSet 声明以及排序后的路径、内容摘要与类型，声明变化须重新建立基线。Git 内部、虚拟环境、缓存、派生索引、报告和 Evidence 目录不纳入此比较；目录链接或越界链接产生故障，文件链接的目标内容也参与摘要。这是检查能力，不是防止并发写入的锁或完整的宿主隔离。

配置的审计事件文件也排除在范围比较之外，以免正常记录验证事件造成自触发的越界；对于旧基线中已记录的该文件，比较时同样排除，基线原始摘要保持不变。审计文件的完整性由审计校验承担。

## 7. 依赖、审计与验证设计

只允许依赖 core。Workflow Engine 通过注入的阶段处理协议编排服务，不导入 design、verification、adapters 或 cli 实现。决策计算尽量无副作用，状态与审计写入由应用/端口完成。

审计记录保留策略版本、事实摘要、调用者身份来源、决策和原因。当前状态可重建，历史拒绝或批准记录不被覆盖。配置无法读取和规则自身无效属于故障，检查发现违规属于 blocked，二者不能混淆。

Task/ChangeSet 创建和生命周期迁移追加 `task_created`、`task_transition`、`changeset_created`、`changeset_transition` 事件，并绑定 revision、前后状态和记录摘要。状态文件写入与审计追加不是同一事务；若状态已写入但审计失败，CLI 返回 `EPE-AUDIT-WRITE`，后续检查必须通过摘要和审计完整性重新核对，不能把该次调用当作成功完成。

拟议测试：缺设计、批准失配、伪造身份、风险降级、超范围写入、警告/阻断规则、过期 ADR、事实版本不匹配，均可独立断言决策原因。四类任务缺少各自必要信息时不能激活；旧 revision 的状态写入返回冲突。

测试位置为 `tests/unit/governance/`、`tests/acceptance/gate_cases/`。应直接注入事实验证决策表，并用端到端场景证明事实来自真实检查。

## 8. 工作包与交付条件

WP-01 冻结 Policy/Workflow 和 Task Schema；WP-07 实现权限与门禁；WP-10 完成端到端；WP-14 扩展宿主执行与多 Agent 治理。

交付需具备可解释决策表、风险反例、完整状态审计及 AC-05/11/12。不得将调用者自报 approved、仅文件存在或过期测试结果作为放行依据。

上游：core 模型、可信身份和检查事实。下游：CLI、CI、Agent adapter。返回[模块索引](../README.md)。
