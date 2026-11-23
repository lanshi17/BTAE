# EPE ACP 适配器与本机 Hermes 会话复核（2026-11-23）

- 执行时间：约 2026-11-23 13:35–13:37 UTC；Linux，Python 环境见下列可执行文件。
- EPE 工作树：`f6eea45ce2b0b2784959c54ea738fc7732939407`，执行时干净；`src/epe/adapters/hosts/acp.py` SHA-256 为 `8e2552ee56635ed3d3b8a54e2fd0ab0f0471e05ce2e13f2a613e55a009b59330`。
- 宿主：`/home/lanshi/.hermes/hermes-agent/venv/bin/python -m acp_adapter`；该虚拟环境的 `pip show hermes-agent` 报版本 `0.21.0`，此前 ACP 响应记录为 `0.22.2`，版本来源不一致，不能将二者等同。

## 执行和结果

1. 在仓库执行 `PYTHONPATH=src python -m epe.cli --root /mnt/data/Projects/Systems/01_btae --format json host capabilities --host hermes --transport acp --command-json '["/home/lanshi/.hermes/hermes-agent/venv/bin/python","-m","acp_adapter"]'`，退出码 0；握手结果为 `handshaken-untrusted`，身份、隔离和取消均为 false，操作列表为空。本次握手使用原有宿主环境，不记录其配置值。
2. 将 `HERMES_HOME` 设为空临时目录、禁用 lazy installs，使用 EPE `open_session`，初始化在 20 秒后超时，退出码 1；未能确定具体启动原因，该失败不是协议拒绝的证据。
3. 另建临时 HOME 及 `.hermes/config.yaml`，使用 custom fixture model、`http://127.0.0.1:1/v1`、空 MCP 配置、禁用全部工具和记忆；子进程仅继承 `PATH/LANG/TZ`，再显式设置临时 HOME、Hermes 源码 `PYTHONPATH`、`HERMES_ACP_SKIP_CONFIGURED_MCP=1` 和 `HERMES_DISABLE_LAZY_INSTALLS=1`。通过 `HermesACPAdapter(..., cwd=/home/lanshi/.hermes/hermes-agent, timeout=45).open_session(cwd=临时目录)` 完成初始化及会话创建；输出 `session_opened= True mcp_servers=empty prompt=not_run`，退出上下文后 `session_closed= True`，进程退出码 0。临时目录在结束时清理。

本次未发送 prompt，未连接模型服务，未测试 MCP 工具、宿主身份、写入隔离或取消。会话 ID 未记录。此记录证明上述环境下 EPE 当前传输可连接并关闭会话，不证明生产权限或方法收益。
