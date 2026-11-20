# TASK-audit-field-hardening：审计事件字段严格性

- 分类：Bugfix；风险：高；影响 MOD-009 Audit、MOD-006 Evidence、MOD-007 审批门禁；写入范围为审计校验、测试和设计记录。
- 根因：审计链结构校验只检查 sequence 值相等，布尔值可被 Python 当作整数；timestamp、event_type 和 payload 内容边界不完整，非法事件可能进入 hash 链并影响审批审计判断。
- 设计：事件要求 sequence 为非布尔正整数且与行号一致；timestamp 为带 UTC 偏移的 RFC3339 字符串并规范化为有效时间；event_type 为非空且受限长度字符串；payload 必须为无递归、字符串键、有限数值、可 JSON 序列化对象；hash/previous_hash 为小写 64 位 SHA-256。追加前和读取时使用同一校验。错误不写入新事件，保留原字节。
- 验收：布尔/负序号、非法时间/hash、非对象或递归 payload、超长事件类型均被拒绝；正常追加、并发、短写和 CLI 审计验证回归通过。设计 draft。

- 结果：审计追加和读取统一拒绝布尔序号、非 UTC 时间、非法事件类型、非 SHA-256 摘要和不可 JSON 化 payload；现有并发、短写、CLI 与审批提交回归通过。定向 11 项、全量 173 项通过；证据见 `reports/evaluations/audit-field-hardening.json`。
