# TASK-strict-json-authority-records：权威状态记录严格 JSON

- 类型：Bugfix；风险：高；影响 MOD-007 Governance、MOD-008 CLI、MOD-009 Adapters、MOD-006 Verification。
- 问题：Task、ChangeSet 基线、Lease、Evidence、Context cache 与 Audit 读取器中部分入口使用默认 `json.loads`，重复键可能被静默覆盖，造成 authority 记录的语义歧义。
- 设计：新增共享 `strict_json_loads`，拒绝重复对象键与 NaN/Infinity；接入 Task、基线、Lease、Audit、Evidence、Context cache 和 ChangeSet CLI 读取路径。解析失败保留各模块既有结构化诊断/故障状态，不把坏记录当作缺失或通过。
- 限制：ACP JSON-RPC 与宿主响应仍由协议边界单独处理；该修复不提供记录不可变存储或防止有权写者重写文件的能力。

## 本轮结果

- 新增共享严格解码器；Task、基线和 Audit 重复键回归已覆盖；完整 CLI、图、策略和架构回归结果随 PR 证据记录。
- 追加覆盖审批、ChangeSet、Context、Lease 和 Evidence 的 CLI 读取路径，避免门禁复核阶段重新使用宽松 JSON 解码。
- Schema、契约引用、策略、图快照和随包结果校验器的本地 JSON 读取也统一使用严格解码；ACP/宿主 JSON-RPC 保持协议专属边界。
