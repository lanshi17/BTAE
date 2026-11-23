# 宿主能力矩阵

能力矩阵由 `src/epe/adapters/hosts/base.py` 提供。它记录协议版本、可信身份、写入隔离、进程组控制、取消和可执行操作；`measured` 只表示当前本地实现已经检查过该边界，不表示操作系统或宿主授予了更高权限。

| 宿主 | 身份 | 写入隔离 | 进程组 | 可执行操作 | 状态 |
| --- | --- | --- | --- | --- | --- |
| local-cli | 否 | 否 | 是 | verify | measured |
| Hermes | 否 | 否 | 否 | 无 | unsupported-unintegrated |

本地适配器只接受 `verify` 的结构化请求，并把 `start_implementation`、`finalize` 返回 `unsupported`。请求形状通过校验不等于授权；应用层仍需重新检查 Task、ChangeSet、设计、证据和范围。Hermes 仍需实际宿主连接、身份通道和隔离验收后才能改变矩阵。

`HermesACPAdapter`（`src/epe/adapters/hosts/acp.py`）提供显式 argv 的 ACP `initialize` 探测。握手成功时只返回 `handshaken-untrusted`，进程组控制为本地探针可测；`trusted_identity`、`write_isolation`、`cancellation` 和业务 `operations` 仍保持 false/空集合。它不会创建 session、运行模型或改变默认的 `unsupported-unintegrated` 能力矩阵。

`open_session()` 是单独的探索接口：只发送 `initialize` 和 `session/new`，强制 `mcpServers: []`，返回必须显式关闭的会话句柄。会话句柄的 `prompt(text)` 只允许非空纯文本并返回原始 ACP transport result，`cancel()` 发送 `session/cancel` 通知；普通 prompt 请求不能并发消费同一个响应流，关闭会话会唤醒等待中的请求并返回明确的关闭错误。它们不执行工具、不授予身份，也不是 EPE 操作映射。真实 Hermes 取消仍未实测，因此矩阵仍为 false。

`HermesHostAdapter` 提供命令数组 + JSON stdin/stdout 的协议桥，先执行 capability handshake，再处理请求。默认 handshake 是 `handshaken-untrusted`：只能用于 verify，不能据此授予写入或可信身份；只有外部配置显式标记 `trusted_capabilities=True` 时，桥才允许声明的写入操作。命令失败、非 JSON 或超时返回明确错误/unsupported。

`epe host request` 将结构化请求交给本地或显式 argv 的 Hermes adapter，并把宿主决定映射为统一 CLI 状态。Hermes bridge 的工作目录固定为 `--root` 解析出的仓库根，避免宿主在调用进程的其他目录读取上下文。它不写入 Task、Approval 或 Evidence，也不把请求中的身份来源当作认证；治理门禁和真实验证仍需分别执行。
