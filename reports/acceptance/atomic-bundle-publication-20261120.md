# 运行目录原子发布：本地验证记录

- 目标：MOD-009 / MOD-006，WP-08、WP-10 的并发与产物完整性；时间：2026-11-20 09:28 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树有未提交修改。
- 输入 SHA-256：
  - `src/epe/adapters/artifact_store.py`：`bafe021f30b4a6ccf91c9e3477dc0081dfeb3f6df0351d9bd2d42d0aa195c16d`
  - `docs/modules/adapters/README.md`：`6d66f91e072c812e47c2dcd7b5afacc44fd0aa6fdd0a769b682ce01be82d0bb0`
  - `tests/unit/test_artifact_store.py`：`94fa7dcc724f70addefcbf25af3195056a753a72fe3a27a103915bb989db3837`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/unit/test_artifact_store.py tests/integration/test_evidence_snapshot_integrity.py tests/acceptance/test_ac12_closed_loop.py` | 通过，退出码 0；随后新增的不可用路径测试包含在完整回归中 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

目标空目录在提交瞬间出现的场景使用真实目录与内核重命名操作，注入时机由测试控制；并发测试使用线程。未测量其他操作系统或文件系统的支持情况；不支持原子操作时拒绝发布。此记录不替代 EPE 版本化 Evidence。
