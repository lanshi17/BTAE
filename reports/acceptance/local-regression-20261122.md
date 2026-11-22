# 本地全量回归与架构图检查

- 目标：确认 README 所引用的本地 MVP 检查路径、架构图产物和当前实现可复现。
- 执行时间：2026-11-22 11:04 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1。
- 代码基线：`4898d4d7d448bb1a0ee9566965c10efb80da9754`（本报告和 README 为随后追加的文档提交）。

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，243 个测试，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json policy validate` | 通过 |
| `PYTHONPATH=src python -m epe.cli --format json host capabilities --host hermes` | 通过；Hermes 保持 `unsupported-unintegrated` |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过；发布 315 个节点、440 条边 |
| `python /home/lanshi/.agents/skills/scientific-architecture-diagram/scripts/check_layout.py docs/architecture/figures/btae-target-architecture.drawio --strict` | 通过；`FAIL 0 / WARN 0` |
| `git diff --check` | 通过 |
| `git push origin master` | `Everything up-to-date`（随后追加文档提交前） |

架构图同时用浏览器渲染检查了中文标签、箭头方向和底部说明，没有发现裁切或溢出。渲染检查不替代 draw.io 编辑器中的人工语义审阅。

本记录不证明远程 CI 已执行、分支保护已配置、真实 Hermes 身份/写入隔离已具备，也不证明 BTAE 方法收益已完成外部验证。
