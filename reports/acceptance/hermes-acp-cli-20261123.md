# Hermes ACP CLI 只读握手记录（2026-11-23）

- 代码基线：`339d471`
- Hermes：本机 `hermes-agent` v0.22.2
- 范围：只执行 ACP `initialize`；不创建 session、不发送 prompt、不启用 MCP、不记录凭据。

## 命令

```bash
PYTHONPATH=/mnt/data/Projects/Systems/01_btae/src \
python -m epe.cli --root /mnt/data/Projects/Systems/01_btae --format json \
host capabilities --host hermes --transport acp \
--command-json '["/home/lanshi/.hermes/hermes-agent/venv/bin/python","-m","acp_adapter"]'
```

## 结果

命令退出码为 0，统一结果为 `status=passed`，能力矩阵返回：

- `protocol_version=1`
- `status=handshaken-untrusted`
- `operations=[]`
- `trusted_identity=false`
- `write_isolation=false`
- `cancellation=false`
- `process_group_control=true`

这证明 EPE CLI、HermesACPAdapter 和本机 Hermes ACP 初始化线路可达；不证明 Hermes 身份可信、文件写入隔离、session/prompt 工具权限或取消能力。
