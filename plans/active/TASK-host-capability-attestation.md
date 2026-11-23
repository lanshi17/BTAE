# TASK-host-capability-attestation：宿主能力证明

- 类型：Feature；风险：high；涉及 MOD-009、HostPort 和项目配置 Schema；用户已授权持续实现，不代表 attestation 已获外部信任。
- 问题：旧 bridge 参数 `trusted_capabilities=True` 能把宿主自报的身份/隔离/操作直接提升为 `handshaken`，缺少密码学绑定和重放防护。
- 设计：capability 请求携带每次随机 nonce；宿主可返回 `attestation`（受信身份 ID、nonce、SSH Ed25519 签名）。签名载荷是协议版本、nonce 和去掉 attestation 后的完整 capabilities 对象的规范 JSON，namespace 为 `epe-host-capability`。EPE 从 `host_trust.identities` 的受保护公钥配置验签，并要求身份风险范围覆盖声明操作；缺证明保持 `handshaken-untrusted`，有 attestation 但验签失败则 `handshake-failed`。旧布尔参数不再授予信任，仅保留兼容形状。
- 验收：真实生成 SSH 密钥的有效证明、nonce/字段篡改、冒名、缺失配置、重复/过期 nonce 均拒绝；无证明的现有 fixture 仍可只读 verify；不把能力证明变成 EPE 门禁或文件隔离。
- 限制：信任根仍依赖宿主外部保护的配置和私钥；签名只证明声明来源和新鲜挑战，不证明操作系统实际隔离。Hermes ACP 不自动产生该 bridge attestation，能力矩阵继续保守。
- 本轮补充：操作范围约束现在位于 `verify_capability_attestation` 密码学验证边界，直接调用也不能把签名宿主声明升级为超出信任根的操作。
