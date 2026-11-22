# 本地全量回归与架构图检查

- 目标：确认 README 所引用的本地 MVP 检查路径、架构图产物和当前实现可复现。
- 执行时间：2026-11-22 11:04 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1。
- 运行时代码基线：`d092d7b`（增加仓库内 JSON Schema `$ref` 解析、目标 Schema 校验与拒绝远程引用）。
- 文档与契约跟进：`df519e0`（补充 HostPort 机器契约、研究评测计划并修正路线图链接）。

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，247 个测试，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json policy validate` | 通过 |
| `PYTHONPATH=src python -m epe.cli --format json design validate CONTRACT-HOST-PORT-001` | 通过；HostPort 契约 Schema 可读取 |
| `PYTHONPATH=src python -m epe.cli --format json host capabilities --host hermes` | 通过；Hermes 保持 `unsupported-unintegrated` |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过；发布 319 个节点、442 条边 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate`（图重建后） | 通过；345 个导入检查，无违规或盲区 |
| `python /home/lanshi/.agents/skills/scientific-architecture-diagram/scripts/check_layout.py docs/architecture/figures/btae-target-architecture.drawio --strict` | 通过；`FAIL 0 / WARN 0` |
| `git diff --check` | 通过 |
| `git push origin master` | `Everything up-to-date`（随后追加文档提交前） |
| `git push origin master`（契约与路线图跟进后） | 通过；远程更新至 `df519e0` |

契约引用回归还覆盖不存在目标、远程 URL、无效目标 Schema 和有效仓库内 JSON Pointer；这些场景分别验证失败关闭与合法引用路径。

架构图同时用浏览器渲染检查了中文标签、箭头方向和底部说明，没有发现裁切或溢出。渲染检查不替代 draw.io 编辑器中的人工语义审阅。

本记录不证明远程 CI 已执行、分支保护已配置、真实 Hermes 身份/写入隔离已具备，也不证明 BTAE 方法收益已完成外部验证。
