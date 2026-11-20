# TASK-contract-entity-roundtrip：契约实体注册与 round-trip

- 分类：Bugfix；风险：中；影响 MOD-001 Core Registry、MOD-005 Design、MOD-003 Graph、MOD-008 CLI；写入范围为契约结构校验、模型序列化、生成模板和验收测试。
- 根因：`design create CONTRACT-*` 生成专属 `version/schema` 字段，但 Entity Registry 将 `schema` 判为未知字段；Entity 序列化也会丢失原始契约数据；设计校验只在其他实体引用它时才检查契约，直接校验 Contract 本身不会验证 JSON Schema。
- 设计：Contract 使用通用实体字段加必需正整数 `version` 和对象 `schema`；JSON Schema 定义显式条件结构。Registry 保留 Contract 规范字段并 round-trip 到图快照；`validate_design` 对 Contract 自身执行 `validate_contract`。生成模板补齐设计状态。无效 JSON Schema、版本类型和额外结构均以诊断拒绝。
- 验收：生成的契约可被 inspect、graph build、validate；其 schema/version 在实体注册和图持久化后不丢失；引用方校验能拒绝非法 schema；普通实体仍拒绝未声明 `schema` 字段。
