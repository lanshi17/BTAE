# 合并后本地回归复核（2026-11-23）

- 代码基线：`cf15c4d65726fcd9fc5a9933e9baad8210a43d76`（PR #13 合并提交）。
- 工作树：执行复核前无未提交变更。

## 结果

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q -o addopts=''` | 通过，307 项 |
| `PYTHONPATH=src python -m epe.cli --format json policy validate` | 通过，6 个策略/Workflow 文件有效 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，349 节点、460 边、已发布；摘要 `2b1aea14e755ad4aa474656974e9a76f02b9dfd4c68a256b93780570cc39b936` |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，361 个 import，无循环、违规或 unknown |
| `git diff --check` | 通过 |

该回归只证明合并提交上的本地检查能力；不证明真实宿主身份、工具权限、文件写入隔离、跨平台进程组语义或 BTAE 方法收益。
