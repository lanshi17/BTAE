# TASK-agent-protocol-validation：宿主请求契约校验

- 类型：Bugfix；高风险；范围 MOD-009 Host/Agent 协议校验、Hermes 集成测试与协议文档；不宣称实现宿主隔离。
- 依据：agent-protocol.md、adapters §6、WP-14 T1/T8。现有校验只检查非空字段，允许任意 task/changeset/revision、越界写入模式和非字符串目标。
- 设计：严格校验协议版本字段（当前版本 1）、Task/ChangeSet ID、目标实体字符串、设计 revision 为 64 位十六进制、范围为规范相对路径 glob（拒绝绝对、`..`、反斜杠和空项）、parameters/trusted_identity 类型；操作与能力仍由宿主适配器另行判断。自报 approved/role 不产生授权。返回稳定诊断，不执行外部命令。
- 验收：合法 verify 请求继续接受；错误 ID、revision、范围、类型和缺身份请求阻断；Hermes 未配置仍 unsupported，握手版本不匹配明确失败。
- 限制：请求校验不认证身份、不提供文件系统隔离、不证明宿主响应可信；设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，103 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/agent-protocol-validation.json`。
