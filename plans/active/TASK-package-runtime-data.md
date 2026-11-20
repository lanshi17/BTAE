# 可安装包运行时 Schema

- 类型：Bugfix；风险：medium；涉及 MOD-007、MOD-008。
- Policy 校验不再依赖当前源码仓库存在 `engineering/schemas`；策略和 Workflow Schema 作为 `epe.data.schemas` 包数据随 wheel 发布。
- 已验证 wheel 内容包含运行时 Schema，并在脱离项目仓库的临时目录中执行 `epe init` + `epe policy validate` 通过。
- CI 已加入 wheel 构建、临时虚拟环境安装和源码外 `init/policy validate/host capabilities` 步骤；这仍不等同于远程合并保护已启用。
