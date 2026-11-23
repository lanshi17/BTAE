# TASK-strict-json-engineering-manifests：权威工程 JSON 清单严格解析

- 类型：Bugfix；风险：中；影响 MOD-001 Registry、MOD-002 Parsers、MOD-008 CLI。
- 问题：`engineering/**/*.json` 实体/关系清单在 Registry 装配时直接调用 `json.loads`，重复键会被 Python 的默认解码器静默覆盖，与已严格的文档 JSON/ParseBatch 不一致。
- 设计：工程 JSON 清单统一使用严格 JSON parser；重复键、非法 JSON 与非标准数字产生带仓库相对路径/行号的解析诊断，构图保持 `published=false`。
- 限制：此任务只覆盖 Registry 扫描的权威实体/关系清单，不替代所有 Task、Evidence、Audit JSON 存储读取器的独立严格性审计。

## 本轮结果

- 真实 CLI 子进程回归证明重复 `entities` 键不能覆盖前值后继续发布空图；完整验证证据随 PR 记录。
