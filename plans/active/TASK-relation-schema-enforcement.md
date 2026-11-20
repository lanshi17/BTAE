# TASK-relation-schema-enforcement：关系契约严格校验

- 类型：Bugfix；中高风险；MOD-001 Registry/Relation、Schema、测试和知识模型；保护既有改动。
- 依据：WP-02 T3/T4、relation.schema.json、knowledge-model §2。当前注册器未拒绝 relation 未知字段、缺失 `origin.source`、非布尔 verified 或 verification 多余字段；`affects` 端点也绕过了基本类型检查。
- 设计：注册阶段按关系 Schema 检查字段集合、端点 ID、关系枚举、origin.type/source、confidence、verified 类型；verification 存在时严格检查四个审计字段，verified=true 必须存在，verified=false 携带 verification 也拒绝以免产生矛盾状态。关系类型合法端点矩阵继续执行，`affects` 允许任意已注册目标但不允许空/未知端点。错误关系不进入 Registry。
- 验收：缺来源、未知字段、错误布尔/verification、非法 `affects` 端点和非法矩阵均产生稳定诊断；合法显式/静态/推断关系继续通过；verified 记录需要完整元数据。
- 状态：draft，不代表 Schema 已正式批准。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，106 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/relation-schema-enforcement.json`。
