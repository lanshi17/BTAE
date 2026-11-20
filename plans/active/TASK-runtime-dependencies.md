# TASK-runtime-dependencies：发布运行依赖声明

- 类型：Bugfix；中风险；MOD-009/CLI 发布；范围 pyproject、CI/wheel 验证与安装文档；保护现有改动。
- 依据：WP-11 T1/T3、governance policy validator。`jsonschema` 是运行时策略/Workflow 校验依赖，但仅靠环境预装；源码测试通过不能证明干净 wheel 环境可用。
- 设计：将 `jsonschema>=4.20` 声明为项目运行依赖，保持 `PyYAML`；wheel 外部运行测试在隔离环境执行 init、policy validate、graph build 和 host capabilities。文档区分本地检查可用和远程分支保护。
- 验收：构建 wheel 并在无源码目录的干净 venv 安装后，策略校验正常；依赖元数据包含 jsonschema；CI 仍使用同一命令结果模型。
- 限制：本地执行不证明 GitHub 远程保护已启用；网络安装可用性取决于包索引。状态 draft。

- 本地验证：wheel 构建和 METADATA 检查通过；隔离 venv 外部运行 `init`、`policy validate`、`host capabilities` 均 passed；完整测试 `PYTHONPATH=src pytest -q -o addopts=''`，134 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/runtime-dependencies.json`。
