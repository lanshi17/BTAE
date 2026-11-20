# TASK-entity-schema-enforcement：实体契约严格校验

- 类型：Bugfix；中风险；MOD-001 Registry、实体 Schema、测试和知识模型；保留现有工作。
- 依据：WP-01 D-02/D-14、WP-02 T3/T4。当前实体校验允许空 name、错误 source 字段、implementation/verification 数组中的任意值和非字符串 contracts，导致下游映射与图构建收到非法事实。
- 设计：实体顶层字段按允许集合校验；schema_version=1；id/name/type 为非空字符串；source 只接受 path 及可选正整数 line/column，路径为仓库相对规范字符串；implementation/verification/contracts/relations/extensions 类型严格校验，映射项为对象且 path 非空相对字符串，symbol 可选字符串；关系候选保持由 Registry 专门校验。拒绝未知 source 字段及非法枚举。
- 验收：非法实体不进入 Registry，诊断包含稳定 code；合法现有设计继续通过；不改变正文中普通说明文档的非实体语义。设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，108 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/entity-schema-enforcement.json`。
