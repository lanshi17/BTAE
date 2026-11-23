---
id: MOD-009
type: Module
name: EPE Adapters
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# adapters：基础设施与宿主集成

## 1. 定位与范围

实现外部文件、Git、进程、时钟、身份和宿主能力，使领域逻辑不依赖具体执行环境。对应 PRD-001、PRD-007、PRD-008、PRD-012，支撑 AC-01、AC-06、AC-07、AC-08、AC-10。

当前实现包含文件/配置、Git provenance、受控进程、原子存储、严格字段校验和 hash-chain 审计、`AgentRequest`/`AgentResponse` 协议校验和本地宿主能力矩阵。`local-cli` 只提供可测量的 verify 进程边界，写入隔离和可信身份均为 false；Hermes 的 bridge 能力证明使用 nonce 绑定的 SSH 签名，但真实宿主权限通道仍需独立验收。详见[宿主能力矩阵](host-capability-matrix.md)。

V0.2 交付本地文件/Git/进程/产物和明确受信的身份接入；V1.0 再交付 Hermes 等宿主 adapter。协议请求解析不等于身份认证，范围声明不等于真正锁定文件。

## 2. 端口实现清单

| Adapter | 核心端口 | 主要能力 |
| --- | --- | --- |
| Repository FS | RepositoryPort | 限根读取、存在性检查、受控创建、原始字节摘要 |
| Snapshot Store | SnapshotStore | 单写者、generation 临时写入与原子发布 |
| Artifact Store | ArtifactStore | 不可覆盖产物、摘要、Evidence 完成记录 |
| Git | GitPort | commit/dirty、基线、实际改动与移动路径 |
| Process | ProcessPort | 参数数组启动、超时、取消、输出捕获 |
| Clock | ClockPort | 可注入 UTC 审计时间与单调秒表；生产适配器 `SystemClock` |
| Trusted Identity | IdentityPort | 维护者/CI 可信身份事实、来源说明；`LocalIdentityAdapter` 只返回不可信本地事实 |
| CI / Agent | HostPort | 后续请求接入、宿主权限与执行能力映射 |

逻辑上属于同一模块，不要求一个 adapter 对应一个文件。每个端口的故障、超时和幂等语义必须先定义，再实现具体工具。

## 3. 对外接口草案

```text
RepositoryPort.read(relative_path) -> SourceBlob
RepositoryPort.plan_create(files) -> WritePlan
SnapshotStore.publish(generation, expected_previous) -> PublishedSnapshot
ArtifactStore.append_run(run_id, artifacts, record) -> ArtifactReceipt
GitPort.describe_baseline() -> RepositoryRevision
GitPort.diff_paths(baseline) -> ChangeFacts
ProcessPort.run(argv, cwd, allowed_env, timeout) -> ProcessOutcome
IdentityPort.resolve(trusted_execution_context) -> TrustedIdentityFact
```

具体 adapter 只产生基础事实与存储回执，不批准设计、不决定门禁通过、不自行修改状态机。领域服务不得依赖 Git 命令原始输出格式。

## 4. 文件与快照安全

项目配置由随包 `project-config.schema.json` 校验；YAML 必须可表示为 JSON，未知字段和类型错误均作为配置诊断拒绝。纳管目录、模块目录、策略与存储路径须为规范仓库相对路径且解析后位于仓库内；模块实体有效性和归属冲突由图构建检查。所有读写规范化到仓库根，拒绝绝对外部路径、`..` 和符号链接逃逸；敏感路径不因 glob 匹配而放行。实际打开/创建时重新验证父目录和目标，不能只在预检时判断。

初始化写入先预检所有目标，对新文件采用不覆盖创建；发生冲突保留已有文件。新建目录/文件的回滚仅限本次拥有的内容，不能清理后来被用户修改的文件。

快照采用临时 generation、完整校验和 `current.json` 单点原子发布，旧 generation 保留用于恢复。兼容的根级 JSON 视图是非权威视图；指针存在时读取 generation，校验其摘要与指针一致。仓库级单写者锁只保护 EPE 自己的写入；无法阻止外部编辑器修改代码，因此仍需验证前后指纹。锁异常恢复需确认持有者已失效，不能见到旧时间戳就删除有效锁。

## 5. Git、进程与产物规则

Git 无提交时返回 commit=null，不伪造基线；dirty 包括纳管范围内未跟踪文件。范围检查收集新增、删除、重命名前后和二进制文件，不能只看 `git diff` 默认跟踪文件差异。

进程用 argv 数组启动，不启用 shell 插值。stdin 写入与 stdout/stderr 排空并行，输入短写会重试，未完全发送时标记 `stdin_incomplete`，宿主桥拒绝此类响应；stdout/stderr 分流并分别限制保留字节数；达到上限后继续排空并标记各流截断状态，避免子进程阻塞。超时/取消在 POSIX 上向本次 session 进程组发送 SIGTERM，宽限期后升级 SIGKILL；其他平台仅保证直接子进程，不声称进程组隔离。日志脱敏不得破坏退出码与测试计数事实。

本地 ArtifactStore 通过仓库根目录描述符拒绝符号链接组件，以同目录临时文件、fsync 和独占硬链接原子发布；目标已存在时拒绝覆盖。验证运行的日志、测试摘要和 Evidence 先写私有 staging 目录，再以目录重命名一次性提交，失败不发布部分 run 目录。验证日志、测试摘要及 Evidence JSON 由此存储，先发布产物再发布记录。外部命令生成的预期产物仍由执行器校验来源状态与摘要。读取时核对摘要；过期/丢失产物返回缺失事实，不制造空产物满足验证。外部 CI 产物需有持久定位与完整性信息，链接可访问性不代表可信来源。

运行目录发布使用 Linux `renameat2(RENAME_NOREPLACE)`，由内核原子拒绝已有目标，包括检查时不存在但提交前新建的空目录。平台、C 库或文件系统不提供该操作时拒绝发布并报告故障，不退化为存在性检查后普通重命名；单文件硬链接发布仍按其自身平台要求工作。

## 6. 身份与宿主边界

本地 `LocalIdentityAdapter` 明确返回 `trusted=false` 和 `source=local-process`，不读取仓库 reviewer 名称，也不将 role/approved 参数升级为身份事实。本地执行仅接受项目维护者明确配置的受信通道；一份普通仓库 YAML 中的 reviewer 名称不能自我证明。可信配置的控制位置、CI 身份来源和批准记录接收方式是 WP-01 必须解决的设计项，在其实现前高风险操作只能标为不可确认。

Agent adapter 将请求转为共享协议值对象，由外部注入的应用处理器响应，不导入 CLI 或具体领域服务。这样 adapters 仍只依赖 core，宿主 SDK 留在最外层。

宿主若没有文件系统限制、合并保护或可信执行环境，必须在能力描述中声明检查可绕过。不得把本地 CLI 返回“允许”宣传为不可绕过的执行令牌。

## 7. 验证设计

- `..`、符号链接逃逸和创建期间路径变化均被拒绝或产生明确故障。
- 无提交、脏工作树与未跟踪文件纳入来源事实，rename 包含两个路径。
- 写锁冲突、进程中断、部分 generation、磁盘写失败不发布完整成功结果。
- 子进程派生孙进程后超时，整个本次进程组被终止；其他进程不受影响。
- 篡改产物摘要、丢失产物与身份自声明被准确区分。
- 审计追加使用本地文件 advisory flock 序列化并在锁内校验已有链；读者使用共享锁。锁不约束无协作进程或文件替换，哈希链不能检测整链或尾部删除。清除索引不删除审计记录。

拟议测试为 `tests/unit/adapters/` 与临时目录/仓库/进程的集成测试。V0.2 首选本地 Linux；其他平台能力在测试后声明，不提前承诺进程组语义跨平台一致。

## 8. 工作包与交付条件

WP-02 提供最小文件/Git/Clock 端口实现；WP-05/08 加入快照、进程和产物；WP-06/07 完成身份接入；WP-10/11 验证恢复与 CI；WP-14 集成宿主。

交付必须列明支持平台、可信边界、锁恢复、产物保留和权限局限，并通过对应集成验收。未实现的宿主能力返回 unsupported，不模拟成功。

上游：core 端口契约。下游：通过注入使用外部能力的服务与 CLI。返回[模块索引](../README.md)。
