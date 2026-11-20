# TASK-project-config-contract：项目配置机器契约

- 分类：Feature；风险：中；影响 MOD-009 Repository、MOD-008 CLI 和全部配置消费者；写入范围为项目配置 Schema、配置读取、测试与设计文档。保留已有工件。
- 依据：工程协议要求机器契约与安全边界；当前 `load_config` 仅验证顶层对象，列表、路径及模块归属错误可能导致异常，路径配置亦可能逃出仓库。
- 设计：增加随包提供且仓库同步的 JSON Schema，覆盖现行 `schema_version`、project_id、managed（含 module_roots）、exclude、policies、storage 和 approval_trust。入口使用随包 Schema 校验，先检查 YAML 可表达为 JSON（字符串键、有限数字、无递归）；配置路径限制规范仓库相对路径并检查解析后不越界；配置读取失败返回结构化诊断，所有 CLI 用例一致拒绝。字段缺省沿用现有默认行为，不接受未知字段。模块实体是否存在、归属是否冲突仍由构图检查。
- 验收：默认配置和现有签名配置可用；模块归属错误、错误集合类型、未知字段、绝对/穿越/符号链接路径及不可序列化 YAML 均结构化拒绝，真实 CLI 无 traceback；验证源码与打包 Schema 一致。设计 draft。

- 结果：项目配置 Schema 已在仓库与包数据中同步，入口统一校验类型、未知字段、路径和 JSON 可表达性。真实 CLI 错误无 traceback；定向 16 项、全量 168 项通过；wheel 构建成功且包含 Schema。证据见 `reports/evaluations/project-config-contract.json`。
