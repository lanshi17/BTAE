# TASK-hermes-acp-exploration：真实 ACP 传输探索

- 类型：Exploration；状态：in_progress；设计状态：draft。
- 问题：现有 HermesHostAdapter 要求一次性 JSON bridge；已安装 Hermes 使用长期 ACP JSON-RPC 会话，两者不能直接对接。
- 假设：EPE 可通过受限 ACP 客户端完成版本协商和会话交互，再由应用层独立检查治理事实；ACP 初始化不提供可信身份或写入隔离证明。
- 范围：Hermes ACP 协议探测、适配设计和独立测试；保护现有 HostPort 和审批/执行边界。不运行模型任务或修改 Hermes 配置。
- 风险：启动可能加载宿主环境和启动钩子；模型调用、工具执行及网络访问须单独约束。探针仅发送 initialize，不创建会话。

## 原型设计

1. 启动明确配置的 argv，使用仓库目录；stdin/stdout 持续打开，stderr 与协议流分离。为启动、请求、总运行时间和输出设上限；超时、EOF、错误 JSON、重复或错误 ID 必须失败关闭。
2. 以 ACP `initialize` 的 JSON-RPC 请求协商协议版本，核对响应 ID、版本及 agent 信息；允许异步通知，但不将任意通知视为结果。
3. 初始化成功只证明传输可达。`trusted_identity`、`write_isolation`、取消和进程树控制分别保持 unknown/false，直到通过对应外部实测。
4. 后续操作需要明确的 ACP session 生命周期、用户批准的工具权限和取消协议；先定义权限模型与拒绝路径，再实现 `session/new`、`session/prompt` 和 EPE 操作映射。不得把模型文本或 ACP 自述当成门禁通过。
5. 单元测试使用受控子进程覆盖分帧、通知、错误和超时；真实 Hermes 探测独立记录版本、命令、环境、结果与范围，不访问或记录凭据。

## 已执行的实验

- 2026-11-23：使用已安装 Hermes Agent 0.22.2 的 ACP 模块，发送 JSON-RPC `initialize`（协议版本 1），得到匹配 ID 的成功响应；响应声明 `agentInfo.name=hermes-agent`、`protocolVersion=1`。
- 将 `HERMES_HOME` 指向空临时目录时，安装器尝试准备隔离依赖，20–45 秒内未完成；该超时不是 ACP 协议拒绝。现有安装目录探针成功，但加载了现有 Hermes 环境文件；未记录文件内容。
- 实验未创建 session、发起模型调用或测试工具权限，因此不证明端到端集成、可信身份、文件隔离或取消。
- 后续原型：`experiments/hermes_acp_probe.py` 在真实 Hermes 安装目录运行 `python /mnt/data/Projects/Systems/01_btae/experiments/hermes_acp_probe.py --timeout 20 -- /home/lanshi/.hermes/hermes-agent/venv/bin/python -m acp_adapter`，返回 `hermes-agent`、版本 `0.22.2`、ACP 版本 1；结果显式标识 `initialize_only`，身份与写入隔离均为 false。路径依赖本机安装，不是可移植安装说明。
- 正式代码原型：`src/epe/adapters/hosts/acp.py` 的 `HermesACPAdapter.handshake()` 复用同一失败关闭边界，成功结果为 `handshaken-untrusted`，不声明业务操作；`tests/integration/test_acp_adapter.py` 覆盖受控子进程与真实边界语义。
- `open_session()` 仅发送 `initialize` 和 `session/new`，固定空 MCP 列表并返回显式关闭句柄；会话句柄新增纯文本 `prompt()` transport 原型，但未在真实 Hermes 上创建会话或发起模型调用以避免修改宿主状态和产生推理副作用。

## 验收与决策

原型需重现握手并对上述失败路径做真实子进程测试；发布级集成仍需安全边界设计、版本迁移评审、真实宿主身份/写入隔离及取消实测。探索结果不构成设计批准或生产能力声明。

- 2026-11-23：真实 CLI 只读握手证据见 [`reports/acceptance/hermes-acp-cli-20261123.md`](../../reports/acceptance/hermes-acp-cli-20261123.md)。
