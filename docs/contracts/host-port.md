# EPE HostPort v1（设计草案）

## 1. 目的与边界

HostPort 定义宿主 Agent 与 EPE 之间的结构化请求/响应边界。协议核心不依赖 Hermes、Codex CLI 或其他执行端；宿主能力、身份可信度和文件写入隔离是独立事实，不能从请求字段或宿主自述自动推导。

机器契约位于 [`agent-request.schema.json`](../../engineering/schemas/agent-request.schema.json) 与 [`agent-response.schema.json`](../../engineering/schemas/agent-response.schema.json)。当前版本固定为字符串 `"1"`，变更字段或状态必须发布新协议版本并保留迁移说明。

## 2. 请求契约

请求必须包含：

- `request_id`：非空调用标识；
- `operation`：`start_implementation`、`verify` 或 `finalize`；
- `task_id`：`TASK-` 前缀的任务身份；
- 可选 `changeset_id` 和 `expected_design_revision`；后者为 64 位十六进制摘要；
- 非空 `target_entities`；
- 实现类操作的仓库相对 `write_scope` glob；不得包含绝对路径、`..`、反斜杠或空项；
- 结构化 `parameters`；
- 宿主可信通道注入的 `trusted_identity.source`。

`role`、`approved`、`identity-source` 等调用者可控字段只作为普通数据，不能授予权限。EPE 应在执行前重新读取 Task、ChangeSet、设计版本、策略、范围和证据。

## 3. 响应契约

响应 `decision` 为 `accepted`、`blocked`、`unsupported` 或 `error` 之一，并携带字符串数组 `reasons`、结构化 `diagnostics`、`evidence_ids` 和 `next_steps`。每条 `diagnostics` 必须包含非空 `code`、`severity`（`error/warning/info`）和 `message`，可选定位字段必须符合机器 Schema；bridge 会拒绝非法结构并保留合法诊断。`accepted` 只表示宿主协议和当前适配器能力允许继续，不等价于治理门禁通过；真正的实现和完成决定由 EPE 应用层重新计算。

## 4. 传输与生命周期

Hermes bridge 使用一行 JSON 请求和一行 JSON 响应。请求发送前执行 capability handshake；协议版本、响应类型、输出大小、超时、退出码、取消和 stdin 完整发送状态均须校验。命令数组直接执行，不经过 shell；桥接进程 cwd 固定为调用方解析后的仓库根。

四类工作流的最小边界如下：

| 操作 | 当前本地 CLI | Hermes bridge 默认状态 |
| --- | --- | --- |
| `verify` | 可接受结构化请求并交由应用层形成 ExecutionPlan | 未配置时 `unsupported-unintegrated`；握手后默认 `handshaken-untrusted` |
| `start_implementation` | `unsupported`（无写入隔离） | 未取得外部可信能力证明时 `unsupported` |
| `finalize` | `unsupported`（无写入隔离） | 未取得外部可信能力证明时 `unsupported` |

适配器不写入 Task、Approval 或 Evidence；宿主返回值也不能绕过 `check`、`verify` 或完成门禁。真实 Hermes 身份、权限和隔离仍需外部实测，当前能力矩阵见[宿主能力矩阵](../modules/adapters/host-capability-matrix.md)。

## 5. 兼容性与失败语义

未知协议版本、非法请求、握手失败、非 JSON 响应、超时、输出截断和不完整 stdin 均必须返回可区分的 `blocked`、`unsupported` 或 `error` 诊断，不能降级为空成功。旧版本请求不得通过字段猜测兼容；调用方应显式选择适配器版本并记录实际命令和环境。

本契约仍为设计草案；`verification_status: passed` 只表示仓库内协议正反例和桥接边界测试通过，不表示真实宿主强制执行已经建立。
