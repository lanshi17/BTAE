---
id: MOD-006
type: Module
name: EPE Verification
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# verification：验证与证据引擎

## 1. 定位与范围

执行确定性检查、收集真实运行结果并计算 Evidence 当前有效性，是 VE 的实现边界。对应 PRD-003、PRD-004、PRD-006、PRD-007，覆盖 AC-03、AC-04、AC-06、AC-07、AC-08、AC-12 的验证部分。

不修改业务代码使检查通过，不批准设计，不决定调用者权限。运行结果与门禁决定分开；一次失败检查也可以生成 valid 的诊断证据。

## 2. 逻辑组件

| 组件 | 输入 | 输出 |
| --- | --- | --- |
| Mapping Validator | 设计映射、符号索引、注册快照 | 路径/符号与声明状态的一致性 |
| Contract Validator | 经支持性确认的契约、实现签名/运行数据 | D1/D2 检查事实 |
| Architecture Validator | 图快照、有效规则及例外 | pass/fail/unknown 与违规路径 |
| Test Runner | 已授权 ExecutionPlan、ProcessPort | 退出事实、测试收集数、日志与产物 |
| Evidence Manager | 执行事实、输入清单、环境与摘要 | 不可变记录和当前有效性视图 |

契约定义是否完整由 design 检查；此处检查实现是否符合契约，不能互相代替。

## 3. 对外接口草案

```text
validate_mapping(registry, symbol_index, scope) -> CheckResult
validate_architecture(snapshot, effective_rules) -> ArchitectureReport
run_verification(execution_plan, authorized_run_context) -> VerificationRun
record_evidence(run, before_manifest, after_manifest, artifacts) -> EvidenceWriteResult
assess_validity(evidence, current_inputs, environment_policy) -> EvidenceAssessment
```

ExecutionPlan 固定命令参数数组、工作目录、超时、目标、配置版本、所需产物和结果解析器。它由应用读取配置并经 governance 授权后传入，不从 Task 自由文本构造。

## 4. 映射与架构算法

对 `implemented` 的实体逐项查路径和限定符号，支持一实体多实现、同文件多实体。draft/not_started 中的未来路径报告未实现，不冒充实现完成；完整性策略决定是否在当前工作流阻断。

模块依赖规则使用图中的实际边与 `managed.module_roots` 显式模块归属，返回违反规则的依赖路径和来源。图中同时存在模块和纳管 Python 文件而未配置模块归属时，架构检查将其作为未知覆盖：默认阻断；策略显式设置 `unknown_is_blocking: false` 时报告 `unknown` 和警告，可按该策略继续门禁，但不声称检查通过。图内没有模块或没有 Python 文件时不要求配置模块归属。已发现的违规始终为 fail。无法解析的动态依赖生成 unknown；静态无违规只能描述已分析范围。例外只能使用 governance 提供的有效规则集，不在检查器内部接受未授权 ADR；`exceptions_applied` 只列出实际抑制当前禁止依赖边的例外，范围未命中时原违规保留。

## 5. 一次验证的执行顺序

1. 检查授权运行上下文、配置、环境和存储可用性，生成 Run ID。
2. 采集纳管输入及环境基线，绑定 Task、ChangeSet、有效策略和批准版本。
3. 通过 ProcessPort 启动命令，捕获日志、退出码、计时和测试收集事实；stdout/stderr 各自有保留上限，超出后持续排空并在 Evidence provenance 标记截断。
4. 超时或取消时终止所启动进程组，保留终止原因与部分日志。
5. 采集执行后清单，校验输入是否变化，计算产物摘要。
6. 验证日志、测试摘要和最终 Evidence JSON 通过不可覆盖 ArtifactStore 发布；预期外部产物必须在本次执行期间新建或文件状态发生变化并计算摘要，再发布引用它们的 Evidence 完成记录；产物存储失败时不返回已完成 Evidence。未更新的遗留文件不能证明本次运行。文件状态变化不能证明写入者身份，外部并发修改仍是盲区。失败保留故障记录。
7. 返回结果与有效性视图，由 governance 聚合完成门禁。

代码、契约、测试或有效验证配置在执行中变化，即使退出 0，也标为 stale。生成的日志、Evidence 与索引排除在源输入 manifest 外，避免运行自失效；Task/策略/批准依据单独绑定其版本，不能因此忽略授权变化。

验证策略可配置在默认策略目录之外：运行记录另存实际验证策略的 SHA-256，读取前后及检查结束时比对，重新评估时再次读取。策略变化使证据 stale，策略不可读或旧记录缺少指纹时为 unknown；这一绑定不受普通输入排除规则影响。前后快照不能发现两次采样之间修改后又恢复的变化，不能替代宿主写入隔离。

## 6. 结果解释与有效性

| 场景 | 执行结果 | 门禁相关事实 |
| --- | --- | --- |
| 必需测试实际执行并通过 | passed | 还需证据 valid |
| 断言失败 | failed | JUnit 报告含 failure/error testcase |
| 零收集或零通过测试（即使全 skip） | error | `test_execution_unconfirmed`，不能证明测试完成 |
| 命令缺失 / 结果无法解析 / 产物不可保存 | error | 无法证明完成 |
| 配置要求但未执行 / 取消前未启动 | not_run | 不能作为通过 |
| 执行时输入改变 | 保留真实执行结果 | validity=stale |
| 产物缺失或摘要不符 | 保留原结果 | validity=invalid |
| 环境与来源不足 | 保留原结果 | validity=unknown |

验证策略中每项检查可选 `max_age_seconds` 正整数。配置后，以 Evidence 的 `finished_at` 为起点，超过该秒数时为 stale；时间恰好到达期限仍有效。时间戳缺失、无时区、位于当前时间之后或时钟不可用时为 unknown。还可配置 `allowed_env` 字符串数组；配置后运行器只传递当前进程中列出的环境变量，不记录环境值，仅在 provenance 记录 `environment_mode` 和变量名。未配置时保持继承环境的兼容行为，并明确记录 `environment_mode=inherited`。未配置有效期时不以时间使证据过期；产物完整性和输入、环境校验仍独立执行。上下文解析每次重算有效性，时间到期可使缓存失效。

非测试检查如构建无需提供测试计数；标为测试的检查必须能确认收集/执行事实，不能仅以 shell 退出 0 代替。当前 `result_parser: pytest` 要求与运行器相同的 Python 解释器以 `-m pytest` 启动，由运行器生成 JUnit XML 并统计实际通过的 testcase；不接受只含终端通过摘要的结果。原始 XML 可能含敏感输出，仅保留计数摘要。完成门禁只接受具备 `pytest-junit-v1` 协议和已校验运行专属摘要的 passed 证据；旧版仅有终端文本的记录保留原结果但适用性为 unknown。解释器、测试代码和插件仍需可信，结构化报告不证明测试质量。

Evidence 原始记录不可修改，validity 是对给定当前输入的计算结果，可缓存但缓存可失效。默认全纳管范围保守指纹；缩小依赖闭包属于后续需独立验证的优化。

读取运行记录时，已存在的 `RUN-*` 目录若缺少记录、记录无法解析或缺少确定任务和检查顺序所需的关键字段，必须报告错误并阻断完成检查；不能静默退回较早的通过记录。无法确定损坏记录属于哪个任务时保守阻断所有任务。CLI 验证完成后将运行 ID、任务 ID 和 Evidence 文件摘要追加到本地审计链；完成检查核对相关审计事件，发现整个目录被删除或记录被修改时报告故障。历史无审计事件的记录保持可读，但不能作为有效完成证据，需重新执行验证。发布与审计追加并非事务：中断留下未登记记录时须重新验证；本地链不能检测有权限者同时重写或删除链和全部记录，仍需外部可信审计。

为兼容早期记录，缺少 `environment` 的旧 Evidence 可被解析但有效性只能为 `unknown`；其他 Schema 结构错误仍产生读取故障。

## 7. 依赖、存储与验证设计

只允许依赖 core、graph。Process、ArtifactStore、Repository、Clock 等由 adapters 实现；verification 不直接使用 shell 或宿主 API。运行日志按允许规则脱敏，环境只记录允许列表或摘要，不复制整套环境变量。

拟议产物存于 `reports/tests/`、`reports/architecture/` 和运行专属报告目录，Evidence 审计记录独立保留。清理策略必须保留记录及缺失标识，不能删掉失败记录后只显示通过；具体路径和保留期在 WP-01 冻结。

拟议测试：

- 删除映射符号、引入禁止 import 和循环，分别得到明确事实。
- 运行通过、断言失败、零测试、超时、缺命令、取消样例并保存真实结果。
- 无提交/脏工作树、执行中改输入、环境改变和产物篡改分别识别。
- 失败记录仍可 valid；passed 但 stale 不满足完成要求。
- 产物存储失败不产生已完成 Evidence；并发记录不覆盖 Run ID。

测试位置为 `tests/unit/verification/`、`tests/integration/verification_run/`。进程行为使用可控小程序集成验证，不能只依赖 Mock 证明终止有效。

## 8. 工作包与交付条件

WP-04 交付映射校验；WP-05 交付架构校验；WP-08 交付运行器和 Evidence；WP-10 联合验收崩溃、并发与输入竞态。

交付必须覆盖 AC-03/04/06/07/08，并与治理、CLI 完成 AC-12。EvidenceManager、TestRunner 等核心类实现前补齐独立设计与行为契约。

上游：core、graph、授权运行与外部端口。下游：governance、context、CLI。返回[模块索引](../README.md)。
