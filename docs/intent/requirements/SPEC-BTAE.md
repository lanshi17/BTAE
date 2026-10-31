---
id: SPEC-001
name: BTAE Engineering Protocol Engine Specification
version: 0.1
design_status: draft
implementation_status: not_started
verification_status: pending
---

# BTAE / EPE 工程规格（SPEC）

## 1. 范围与规范用语

本文落实 [PRD](../PRD-BTAE.md) 的 MVP 需求，以[总体架构](../../architecture/overview.md)为结构依据。必须表示验收要求，应表示默认建议，可表示可选能力。本文是拟议规范，字段和接口尚未由可执行 Schema 或代码实现。

目标环境为单仓库、Python 优先、CLI 驱动的 EPE。MVP 支持实体与文档解析、代码映射、基础依赖图、设计与测试门禁及 Evidence。高级检索、语义漂移裁决、跨仓库、多 Agent 锁与完整宿主适配属于后续范围。

## 2. 输入、输出与信任边界

输入为受版本管理的设计、契约、治理配置、任务和代码，以及受信执行端产生的结果。生成索引不是权威输入；从缓存读取前必须匹配输入版本。

仓库内文件不自动等于可信授权。审批者身份由维护者配置或 CI 身份提供，不能接受 Agent 请求中的自声明角色。测试命令只从已授权配置读取，以参数数组执行；任务文本、Markdown 与模型输出不得直接拼成 shell 命令。

路径以仓库根为基准，拒绝 `..` 越界和符号链接解析后逃逸。忽略 `.git/`、`.engineering/`、报告与虚拟环境等非输入目录；显式纳管根由策略声明。解析范围外对象报告为未纳管。

## 3. 数据契约

### 3.1 Entity

| 字段 | 约束 |
| --- | --- |
| `schema_version` | 必填，首版 `1` |
| `id/type/name` | 必填；ID 仓库内唯一且不可复用；类型来自注册枚举 |
| `source.path` | 必填，仓库相对路径；定位信息可补充行号 |
| `design_status` | 适用于设计实体：`draft/reviewed/approved` |
| `implementation_status` | 适用于被实现设计：`not_started/in_progress/implemented` |
| `verification_status` | 适用于验证目标：`pending/passed/failed`，必须关联验证版本 |
| `implementation[]` | 文件路径及可选完整符号名；核心类必须含符号定位 |
| `verification[]` | Test ID 与测试路径引用 |
| `contracts[]` | Contract ID 引用 |
| `lifecycle` | `active/archived`，默认 active；归档不删除身份 |

不同实体使用分类型 Schema，不要求 Source、Evidence 等具备无意义的设计状态。未知字段默认报错，扩展字段放入显式 `extensions`。Markdown 使用 YAML Frontmatter；结构化工件使用同一字段语义。YAML 重复键必须报错。

ID 前缀沿用架构定义；MVP 为实现定位补充 `SRC-`、`SYM-`，为运行补充 `RUN-`。自动发现未注册对象可使用内部定位键，但不得将路径哈希伪装成稳定工程 ID。核心设计 ID 由声明注册，生成器必须检查冲突。

### 3.2 Relation

必填 `from/to/relation/origin/confidence/verified`；confidence 范围为 `[0,1]`。origin 包含 `type: explicit/static/inferred`、源路径和输入指纹。`verified: true` 时必须记录验证者、方法、时间与所依据的版本。

| 关系 | MVP 合法端点 | 基数 / 约束 |
| --- | --- | --- |
| contains | Architecture/Module/Component → Module/Component/Class | 多对多；禁止自环与包含环 |
| realizes | Component/Class → Source/Symbol | 多对多；方向为设计到实现 |
| specifies | Spec → Module/Component/Class/Contract | 多对多 |
| depends_on | Module/Component/Class/Source/Symbol → 同组实体 | 多对多；循环按架构策略检查 |
| conforms_to | Source/Symbol/API/DataModel → Contract | 多对多 |
| verified_by | Spec/Component/Class/Contract → Test/Evaluation | 多对多 |
| evidenced_by | ChangeSet/Task/Test/Evaluation/Component/Class/Contract → Evidence | 多对多 |
| constrained_by | Architecture/Module/Component/Class → ADR/Contract | 多对多 |
| supersedes | 新设计实体 → 同类型旧设计实体 | 多对多；禁止替代环 |
| affects | ChangeSet → 任意已注册实体 | 多对多 |

端点不存在、类型不允许或重复冲突的边必须产生诊断。反向查询由索引实现。模型推断不得单独满足设计、审批或验证门禁。

### 3.3 Task、ChangeSet 与审批

Task 必填 ID、类型 `feature/bugfix/refactor/exploration`、目标、验收条件、风险 `low/medium/high`、目标实体和关联 ChangeSet。分类不确定时需确认或采用较严格策略，不静默降级。

ChangeSet 必填 ID、Task ID、owner、受影响实体、允许写入范围、受保护范围、依赖契约版本、创建时基线指纹与状态 `planned/active/completed/aborted`。受保护范围优先；完成前比较实际改动与声明范围，超范围阻断。

Approval 记录设计 ID、内容指纹、决策 `approved/rejected/revoked`、身份、授权来源、时间和风险适用范围。设计正文、元数据或引用契约变化后原批准不再满足当前门禁；显示状态由当前内容与有效记录共同计算，不能只信 Frontmatter 中的 approved。

### 3.4 Evidence

必须记录：Evidence / Run / Task / ChangeSet ID、目标实体、检查器及版本、实际参数数组、工作目录、起止 UTC 时间、退出码或终止原因、执行结果、环境、输入 manifest、产物路径及 SHA-256 摘要。

执行结果为 `passed/failed/error/not_run`；有效性为 `valid/stale/invalid/unknown`，两者独立。Entity 的 `verification_status` 是针对当前输入聚合得到的视图，不能覆盖历史执行事实。

provenance 包括可空 commit、dirty、Python/OS、依赖锁文件摘要或已安装依赖清单摘要、验证配置、源代码、设计、契约和测试摘要。无提交时 commit 为 null，仍必须有内容 manifest。

## 4. 指纹与证据有效性

文件指纹按原始字节计算 SHA-256；manifest 由按仓库相对路径排序的 `(path, hash)` 列表组成，使用 UTF-8、稳定 JSON 序列化计算总摘要。路径使用 `/`。文件删除、增加或重命名均改变适用输入摘要。

MVP 默认保守地覆盖整个纳管代码/设计/契约/测试集合和有效验证配置，排除生成索引与报告，避免报告写入让自身证据过期。后续可采用经验证的依赖闭包缩小范围；无法确定影响时不能声称未受影响。

执行前后均采集输入摘要；验证过程中输入变化时保留结果，证据标为 stale 并阻断完成。依赖或环境信息不足以判断可移植性时为 unknown。跨环境复用必须满足策略的环境匹配规则，默认要求已记录环境字段一致。

完整性失败为 invalid；输入改变或超过显式有效期为 stale；信息不足为 unknown；其余匹配且来源可信为 valid。未配置时间有效期不自动按时间过期，但仍检查输入与环境。

## 5. 解析、映射和图

文档解析失败、ID 重复、重复 YAML 键和悬空引用必须返回带文件定位的诊断。引用未来尚未实现路径的 draft 设计可作为待办诊断，但不得被实现映射门禁认定为已实现。

Python AST 提取类、函数/异步函数、完整限定名、签名及静态导入。语法错误为分析故障；动态 import、反射和运行注入报告分析盲区。测试路径存在不等于测试发现成功，测试门禁必须取得实际收集/执行结果。

映射校验支持一个设计多个文件及同文件多个实体。已声明 implemented 的实体找不到目标符号时阻断。图包含来源和输入摘要；相同输入应生成相同排序后的实体与边，时间戳不参与内容一致性比较。

图构建必须先校验输入，写临时文件后原子替换索引；失败保留旧索引但标记其过期。MVP 同一仓库单写者，第二个写操作返回冲突，读者只见完整快照；崩溃恢复不得将半成品当作有效索引。

## 6. 状态迁移和门禁

设计正常迁移 draft → reviewed → approved；驳回或内容变化回到 draft 并记录原因，撤销批准使其不再满足门禁。实现 not_started → in_progress → implemented；返工可回 in_progress。验证由实际检查更新，输入改变后当前视图变 pending，历史 Evidence 不改写。

| 门禁 | 必需行为 |
| --- | --- |
| Design Gate | 检查实体、设计/契约完整性、任务范围、风险权限及批准指纹 |
| Mapping Gate | 检查当前实现声明与文件/符号一致 |
| Architecture Gate | 检查配置的禁止依赖与模块循环；例外需有效 ADR |
| Test Gate | 执行必需检查；非零、超时、未运行、零测试收集均不满足测试要求 |
| Finalize Gate | 上述必需项通过，证据 passed 且 valid，实际变更未超范围，索引匹配 |

Low 可由配置的自动规则完成设计审核，Medium 增加独立评审记录，High 必须有经信任来源确认的人类批准。所有适用规则必须版本化，缺失必需策略时返回错误，不能默认放行。

架构检查结果允许 `pass/fail/unknown`。必需阻断规则 unknown 时不能完成；warning 不阻断但必须展示。例外记录规则 ID、实体范围、ADR、批准依据与复查期限，范围不匹配或过期时无效。

## 7. 验证执行与失败处理

检查配置定义命令参数、超时、环境、目标和期望产物。运行器捕获输出及返回码，保留失败证据；超时需终止所启动进程组并记录原因。默认不联网安装依赖或修改源文件；所需准备步骤必须显式配置并获授权。

输出不得保存密钥等敏感环境值；保存允许列表环境摘要并对日志脱敏。若产物不可保存、输入不可指纹或结果无法解析，应记录 error/unknown，而不是 passed。

## 8. CLI 契约

所有命令支持 `--root PATH` 和 `--format text|json`，默认根为当前仓库根、格式 text。JSON 结果仅写 stdout，执行日志写 stderr。

| MVP 命令 | 输入 / 作用 |
| --- | --- |
| `epe init` | 创建缺失配置与模板；冲突返回诊断，不覆盖已有文件 |
| `epe inspect` | 只读列出纳管范围、配置和实现状态 |
| `epe task create --file PATH` | 校验并登记任务；ID 冲突拒绝 |
| `epe task classify TASK-ID` | 返回当前分类和缺失项，不伪称智能推断已完成 |
| `epe design validate ENTITY-ID` | 只读校验设计及相关契约 |
| `epe design approve ENTITY-ID --record PATH` | 验证可信审批记录并登记；不信任调用者自报权限 |
| `epe mapping validate` | 校验纳管实体映射 |
| `epe graph build` | 校验后生成完整索引快照 |
| `epe architecture validate` | 执行配置的静态架构规则 |
| `epe verify TASK-ID` | 按配置执行检查，保存新 Evidence |
| `epe sync` | 重建派生视图，不修改设计意图或审批 |
| `epe check --task TASK-ID` | 综合检查现有门禁与证据，不隐式执行任意测试命令 |

`design create`、`context resolve`、`impact analyze` 为后续接口；若命令暴露但未实现，返回明确 unsupported，不返回空成功。

统一结果包含 `schema_version/command/status/diagnostics/data/evidence_ids`。status 为 `passed/blocked/error/unsupported`；诊断包含稳定 code、severity、message、entity_id、path 和建议动作。退出码约定：0 成功、1 门禁阻断、2 参数或配置错误、3 执行/解析/存储故障、4 不支持、5 写入冲突；多种问题并存时优先报告故障，其次阻断，并保留全部诊断。

查询和重建不得变更权威工件；相同输入重建内容幂等。审批与验证属于可审计写入，每次执行保留独立记录，不覆盖旧 Evidence。初始化的路径冲突必须在写入前预检，避免部分初始化后才发现覆盖风险。

## 9. Agent 操作契约

后续 adapter 请求包括 request_id、Task / ChangeSet ID、目标、期望设计指纹、写入范围和参数；身份从宿主可信通道获取。响应包含 decision、原因、诊断、Evidence 和下一步。

`start_implementation` 在执行前重检设计和范围；`finalize` 在结束前重检证据和实际改动。MVP CLI 不构成文件系统权限边界；没有宿主隔离和必需 CI 时，只能声明检查可用，不能声明写入无法绕过。

## 10. 验收与需求追溯

| 验收 ID | PRD 需求 | 必需场景与预期结果 |
| --- | --- | --- |
| AC-01 | PRD-001 | 在已有工程 init，原文件字节不变；冲突可定位 |
| AC-02 | PRD-002 | 重复 ID、重复 YAML 键、悬空边分别产生错误诊断 |
| AC-03 | PRD-003 | 多文件映射通过；删除已实现类的符号后映射阻断 |
| AC-04 | PRD-004 | 指定禁止导入与模块循环均被发现；动态盲区显式报告 |
| AC-05 | PRD-005 | 缺设计、过期批准、High 无授权和超范围写入分别阻断 |
| AC-06 | PRD-006 | 通过、失败、零测试、超时、缺命令均得到不同且真实结果 |
| AC-07 | PRD-007 | 无提交或脏工作树仍记录真实指纹；修改源/契约/测试后证据 stale |
| AC-08 | PRD-007 | 修改产物摘要导致 invalid；环境信息不足为 unknown |
| AC-09 | PRD-008 | JSON 可解析，退出码符合约定，失败日志不污染 stdout |
| AC-10 | PRD-004/008 | 删除索引后重建内容一致；失败不发布部分图；并发写入返回冲突 |
| AC-11 | PRD-009 | 四类任务均可登记和校验；缺少验收或范围信息不能激活 |
| AC-12 | PRD-005/006/007 | 同一任务形成设计→实现→测试→证据闭环；验证时修改输入后不能完成 |

自动化测试和样例工程必须独立断言以上行为，并保存执行结果。文档中的验收表不表示测试已经实现或通过。

## 11. 冻结前需补齐的机器工件

实体/关系/Evidence/Task/ChangeSet/Approval Schema，Policy 与 Workflow 定义，文档模板，检查器与 CI 配置，以及可信身份/审批 adapter 契约。性能基线与可支持仓库规模在可运行原型上测量后确定；当前不承诺未经测量的耗时指标。

本文与 PRD、架构发现冲突时必须显式修订并评审，不由 Agent 隐式选取较宽松规则。任何字段、状态、退出码或授权变化都应保留版本与迁移说明。
