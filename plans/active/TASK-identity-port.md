# TASK-identity-port：保守本地身份适配器

- 类型：Feature；高风险边界；MOD-009 IdentityPort、Host 文档和测试；不改变 SSH 审批验签逻辑。
- 依据：adapters §6、WP-06/14、core IdentityPort。当前没有统一 IdentityPort 实现，调用方只能直接读取配置或请求字段，容易把显示身份误当可信事实。
- 设计：新增 `LocalIdentityAdapter`，只返回结构化本地执行事实：来源 `local-process`、可信标记 false、kind unknown、id 可选且不作为批准主体。它不读取仓库 reviewer 配置，不从 `role/approved` 参数推断身份。宿主或 CI 适配器必须显式提供可信实现，缺失时高风险门禁继续 unknown/blocked。
- 验收：默认身份永不 trusted；请求字段和仓库配置不能改变结果；输出稳定字段供治理消费；文档明确本地 CLI 无可信身份。
- 限制：本适配器不是认证系统；不会证明操作系统用户、CI/OIDC 或 Hermes 身份。状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，135 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/identity-port.json`。
