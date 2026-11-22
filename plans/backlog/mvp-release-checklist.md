# BTAE / EPE MVP 发布清单

状态：`in_progress` · 更新时间：2026-11-22

这份清单只记录当前仓库可追溯的发布条件；勾选不代表远程分支保护、宿主权限或方法效果已经获得外部证明。

## 本地可复现检查

- [x] `PYTHONPATH=src pytest -q` 全量测试通过。
- [x] `git diff --check` 通过。
- [x] `epe graph build` 和 `epe architecture validate` 可运行。
- [x] `epe policy validate`、`epe audit verify`、`epe host capabilities` 可运行。
- [x] `epe host request --host local-cli --operation verify ...` 的结构化协议路径有测试。
- [x] wheel 在源码目录外安装后可读取全部运行时 Schema。
- [x] CI 工作流包含测试、策略、图、架构、审计、宿主能力和 wheel 隔离检查。
- [x] CI 工作流上传 JUnit 测试报告 artifact。

## MVP 行为验收

- [x] AC-01 至 AC-12 各有自动化测试入口。
- [x] 失败、阻断、未执行、stale、invalid、unknown 和 unsupported 状态可区分。
- [x] Evidence 与审计事件保留运行、任务、ChangeSet 和摘要绑定。
- [x] Task/ChangeSet 生命周期审计和 revision 冲突有回归测试。
- [x] 初始化、Task 创建、Artifact bundle 和图 generation 有并发/冲突防护。
- [x] 文档、Python AST、影响传播、上下文缓存和环境允许列表有回归测试。

## 外部或后续条件

- [ ] 在实际 Git 托管平台确认受保护分支和必需 CI 检查；当前仓库只提交工作流配置。
- [ ] 在目标平台实测 Hermes 身份、写入隔离、取消和进程组能力；当前 Hermes 状态仍为 `unsupported-unintegrated`。
- [ ] WP-10 的完整故障注入、平台矩阵和恢复证据完成独立记录。
- [ ] WP-12/WP-13 的独立真实影响标注集、相关性、召回率和成本基线完成。
- [ ] WP-14 的完整宿主工作流、多 Agent 协作和架构差异协调完成。
- [ ] BTAE 与对照方法的长期试点和消融实验完成；不得以本清单宣称方法收益。

## 发布限制

在所有外部条件关闭前，发布说明只能称为“本地 MVP 检查能力”，不能称为宿主强制执行、远程合并门禁或已验证优于其他工程方法。
