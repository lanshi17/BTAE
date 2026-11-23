# BTAE / EPE

本仓库包含 BTAE（Bottom-Up Traceable Agentic Engineering）的本地工程协议引擎 MVP。实现位于 `src/epe/`，权威设计和规格位于 `docs/`，机器约束位于 `engineering/`。

## 架构概览

下图展示 BTAE / EPE 的目标架构，包括七层工程责任、治理平面、工程知识图谱和逻辑模块。它是设计草案，不代表所有目标能力或宿主集成均已实现；七层也不规定瀑布式执行顺序。

![BTAE / EPE 目标架构](docs/architecture/figures/btae-target-architecture.svg)

可下载 [可编辑的 draw.io 图](docs/architecture/figures/btae-target-architecture.drawio)或 [PDF 版本](docs/architecture/figures/btae-target-architecture.pdf)。架构的设计依据和模块边界分别见[总体架构](docs/architecture/overview.md)和[模块与依赖边界](docs/architecture/boundaries.md)。

本地回归记录见[2026-11-23 本地复核](reports/acceptance/local-regression-20261123.md)，远程执行记录见[2026-11-23 GitHub Actions 复核](reports/acceptance/remote-ci-20261123.md)，分支治理记录见[2026-11-23 远程分支治理复核](reports/acceptance/remote-governance-20261123.md)，逐包边界见[本地 MVP 完成审计](reports/acceptance/local-mvp-completion-audit-20261122.md)。当前代码基线的本地与 GitHub Actions 检查均已通过；`master` 已配置保护规则，真实 Hermes 权限仍未验证。

## 本地运行

MVP 上手和故障恢复步骤见 [使用指南](docs/standards/user-guide-mvp.md) 与 [恢复手册](docs/standards/runbook-recovery.md)。

无需安装到系统环境时可使用 `PYTHONPATH=src`：

```bash
PYTHONPATH=src python -m epe.cli --format json init
PYTHONPATH=src python -m epe.cli inspect
PYTHONPATH=src python -m epe.cli graph build
PYTHONPATH=src python -m epe.cli --format json graph path SRC-src/epe/cli.py SRC-src/epe/core/models.py --direction out --budget 100
PYTHONPATH=src python -m epe.cli --format json changeset conflicts
PYTHONPATH=src python -m epe.cli --format json changeset lease inspect CHANGE-001
PYTHONPATH=src python -m epe.cli --format json audit verify
PYTHONPATH=src pytest -q
```

任务已关联 ChangeSet 后，可填写 `engineering/templates/changeset.yaml` 并运行 `epe changeset create --file PATH` 登记当前范围基线。完成检查会比较基线后的新增、修改和删除；审计目录、缓存、虚拟环境和报告不在比较范围内，具体边界见 [治理模块设计](docs/modules/governance/README.md)。

多 Agent 开始修改前可运行 `epe changeset conflicts` 查询 planned/active ChangeSet 的潜在范围重叠；该命令只报告保守候选，不提供锁或宿主隔离。

遵守 EPE 协议的参与者可用 `epe changeset lease acquire|renew|release|inspect` 管理短期本地租约；租约过期可恢复，但不构成操作系统或宿主写入隔离。

`epe graph path` 在新鲜图快照上返回带原始边证据的最短路径；`--direction`、`--relation` 和 `--budget` 控制搜索范围。路径中的推断、低置信度或未知来源会标记为 `candidate`，找不到路径不等于证明工程中不存在依赖。

缺少设计时可运行 `epe design create CLASS-001`（或其他已支持实体前缀）生成草案模板；命令不会覆盖已有文件。契约设计使用 `CONTRACT-` 前缀和 YAML Schema 字段，审批必须使用配置的受信 SSH 公钥签名。

任务可用 `epe task transition TASK-001 activate|complete|abort` 进行受约束的生命周期迁移；bugfix/refactor/exploration 分别需要复现、基线或假设字段。完成时系统重新执行只读综合门禁，不接受调用者自报通过结果。

审批导入会追加本地 hash-chain 审计事件，可用 `epe audit verify` 检查；这能发现篡改但不替代远程不可变审计或宿主权限保护。

可用 `epe policy validate` 在运行任务前统一检查架构、验证和 Workflow 配置。

架构策略的 `exceptions` 只能引用注册快照中 `design_status: approved` 且仍在复查期限内的 `ADR-*` 实体，并同时匹配规则 ID 与当前依赖边的 `from`/`to` 范围。范围未命中的例外不会出现在 `exceptions_applied`，原规则继续生效；ADR 状态、复查时间或策略结构无效时命令返回 `error`。`epe architecture diff` 会在 `expected_architecture` 中保留同一份应用记录。

也可以在虚拟环境中执行 `pip install -e .`，随后直接使用 `epe` 命令。`epe init` 只创建缺失的治理配置，发现内容冲突会在写入前返回 `blocked`，不会覆盖既有文件。

运行时策略 Schema 已随 wheel 包发布，因此安装后的 `epe policy validate` 不依赖当前源码仓库的 `engineering/schemas` 目录。

当前 MVP 支持实体/关系解析、Python AST 与映射、基础依赖图、架构校验、任务登记、ChangeSet 基线、设计生成/契约校验、签名审批、授权检查运行、Evidence 新鲜度和综合 `check`；同时提供基于图的可解释 `impact analyze`、增量计划和带失效缓存的无外部语义服务 C0–C2 `context resolve`。Hermes ACP 目前仅提供受限探索会话：普通请求单线程读取响应，可接收流式 `session/update`、创建空 MCP 子会话并在已登记的父/子会话间路由请求，关闭会话会唤醒等待者；bridge transport 还支持 nonce 绑定的 SSH capability attestation，但真实 Hermes ACP 不自动提供该证明。这些能力不授予宿主身份、写入隔离、工具权限或 EPE 操作能力。尚未配置宿主文件系统隔离。

能力状态和边界见[宿主能力矩阵](docs/modules/adapters/host-capability-matrix.md)。`local-cli` 只接受只读 `verify` 请求；Hermes bridge 必须显式提供 argv 并完成 capability handshake，未受签名证明的声明保持 `handshaken-untrusted`。ACP 仅提供 POSIX 下的受限会话传输，真实宿主身份、工具权限、写入隔离、跨平台语义和远程不可变审计仍未完成。

CLI 的 JSON 输出遵循 `engineering/schemas/command-result.schema.json`，退出码为：0 成功、1 门禁阻断、2 参数/配置错误、3 执行或存储故障、4 未支持命令、5 写入冲突。

本项目没有将实现状态等同于方法效果验证。PRD 中的收益、召回率和成本指标仍需独立试点与验收记录。

完整本地回归使用 `PYTHONPATH=src pytest -q -o addopts=''`；wheel 脱离源码树的安装验证、CI 运行和分支治理证据分别见[发布回归记录](reports/acceptance/wheel-regression-20261123.md)、[远程 CI 复核](reports/acceptance/remote-ci-20261123.md)和[远程治理复核](reports/acceptance/remote-governance-20261123.md)。测试和 fixture 只证明记录的本地场景，不替代真实宿主权限、独立影响标注集或长期试点。
