# TASK-policy-schema-enforcement：策略与工作流 Schema 执行

- 类型：Bugfix；中高风险；MOD-007 策略校验、CLI policy validate、Schema 与测试；保留现有改动。
- 依据：WP-01 T4/T9、WP-07 T1/T8、governance §1。当前 workflow 只手工检查三个字段，未应用 workflow.schema.json；策略 Schema 对检查项的结构约束不足，policy validate 与 verify 行为不一致。
- 设计：统一用 Draft 2020-12 Validator 校验 architecture/verification policy 和所有 workflow 文件；拒绝未知字段、错误版本、非法类型和越界策略路径。对 verification 策略执行语义检查：checks 必须非空、ID/argv 唯一且非空、timeout 有限正数、pytest 解析器只能与 test kind 配套；保留 Schema 错误与语义错误的稳定诊断。策略文件符号链接拒绝，不能通过路径解析绕过权威路径。
- 验收：无效 workflow 与未知字段被 policy validate 拒绝；空 verification checks 被拒绝；合法策略通过；CLI 输出 error 而非空成功。设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，103 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/policy-schema-enforcement.json`。
