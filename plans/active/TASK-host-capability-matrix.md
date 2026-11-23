# 宿主能力矩阵与拒绝边界

- 类型：Feature；风险：high；涉及 MOD-009、MOD-008、MOD-007；依据 Agent Protocol 和 WP-14。
- 本地宿主能力被显式测量为：可执行 verify 进程组、不可提供可信身份、不可提供写入隔离；start/finalize 返回 unsupported。Hermes 只登记协议版本和未集成状态，不模拟成功。
- `HermesHostAdapter` 已提供参数数组 + JSON line handshake/dispatch 桥；未提供外部可信 attestation 时标记 `handshaken-untrusted`，只允许 verify，不能授予写入或身份信任。
- 验收覆盖机器可读矩阵、本地写入拒绝、协议形状错误和 Hermes unsupported。实际 Hermes、CI 身份及宿主沙箱仍需外部集成验证。

## 本地验证

同一套测试运行 47 项通过；`epe host capabilities`、`graph build` 和 `architecture validate` 的实际 JSON 输出保存在 [执行记录](../../reports/evaluations/iteration-all-modules-002.json)。

能力自述现在可选地通过 `host_trust` 的 nonce 绑定 SSH attestation 验证；缺少证明仍保持 `handshaken-untrusted`，不改变当前 Hermes 能力矩阵。
