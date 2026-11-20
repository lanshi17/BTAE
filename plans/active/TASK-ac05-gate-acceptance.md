# TASK-ac05-gate-acceptance：设计授权与范围门禁验收

- 分类：Feature；风险：中；影响 MOD-005 Design、MOD-006 Verification、MOD-007 Governance、MOD-008 CLI；写入范围为 AC-05 验收测试、计划和证据。
- 依据：SPEC AC-05 要求缺设计、过期批准、High 风险无授权、超范围写入分别阻断。现有签名测试在进程内 CLI 验证批准版本变化；ChangeSet 超范围场景也未统一为独立子进程 AC 测试。
- 设计：真实子进程 CLI 临时工程分别运行四种变体；准备有效任务、ChangeSet、图和真实检查 Evidence，确保目标故障是主要阻断原因。High 有效批准使用临时 Ed25519 密钥及真实 `ssh-keygen` 签名；设计变更后重建图并重跑检查以隔离批准 revision 失配。无设计目标仍运行检查以验证 design missing 诊断。超范围场景在登记基线后修改 protected 文件。
- 验收：缺设计、High 无批准、已签批准过期、protected 路径变化四种场景均由 `check` 子进程返回非通过和指定诊断；已签批准控制场景先通过。无 Mock 身份/文件系统/执行器。

- 结果：真实 CLI 四类门禁负例均被阻断；高风险签名批准控制场景先通过，改变设计 revision 后被拒绝；纳管范围外但属于 ChangeSet 保护路径的 README 修改单独产生 scope 阻断。定向 3 项、全量 182 项通过；证据见 `reports/evaluations/ac05-gate-acceptance.json`。
