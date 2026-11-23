# 宿主能力证明合并后复核（2026-11-23）

- 代码基线：`a942dd8ab6d77f9b310614d7a9055ecb3d997e1d`（PR #15 合并提交）。
- 范围：EPE JSON bridge 的 capability attestation；不声称真实 Hermes ACP 自动提供证明。

## 已验证

1. 生成真实 Ed25519 密钥并用 OpenSSH `ssh-keygen -Y sign/verify` 验证完整 capabilities 载荷；签名绑定每次随机 nonce。
2. 修改 nonce、能力字段或签名、缺失 `host_trust` 信任根、空操作范围均拒绝。
3. 未签名 bridge 即使声明 `trusted_identity`、`write_isolation` 和实现操作，也保持 `handshaken-untrusted`，最多保留 `verify`。
4. 保护规则拒绝使用旧 `trusted_capabilities` 布尔值提升信任；有效证明且配置操作范围匹配时才返回 `handshaken`。

## 合并后命令

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q -o addopts=''` | 通过，313 项 |
| `PYTHONPATH=src python -m epe.cli --format json policy validate` | 通过 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，352 节点、469 边 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，370 个 import，无违规或 unknown |
| `git diff --check` | 通过 |

信任根公钥配置和宿主私钥仍需外部保护；签名不证明真实文件隔离、工具权限或操作系统身份。当前真实 Hermes ACP 能力矩阵继续保守为未受信。
