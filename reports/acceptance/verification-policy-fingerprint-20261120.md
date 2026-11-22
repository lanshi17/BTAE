# 验证策略指纹修复：本地执行记录

- 目标实体：MOD-006；关联 AC-07、AC-08。
- 时间：2026-11-20 09:07 UTC 附近；环境：Linux，Python 3.14.4，pytest 9.1.1。
- Git 基线：`caf7831`；执行时工作树有未提交修改，下列 SHA-256 标识相关输入，不代表提交。
- `src/epe/verification/runner.py`：`5e98c7176a589418ad56538ba79fc5b747de9e853a0c5fd10d1eff5a89633b40`
- `tests/integration/test_evidence_snapshot_integrity.py`：`92a69963d62596e5d7159c64b5863d67411e2b5b970b5a9339a977b520d469b5`
- `docs/modules/verification/README.md`：`93e2eb825ceae9c41715c984a0eaccb102416cfecf9e69c96e3efc69ac08fa3c`
- `.github/workflows/ci.yml`：`0aee0d682625f7ee34579edbfe6960dfd808a7f8994c6721da48cffd89797fb9`

| 实际执行命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/integration/test_evidence_snapshot_integrity.py tests/acceptance/test_ac07_provenance_cli.py tests/acceptance/test_ac08_evidence_validity_cli.py tests/acceptance/test_ac12_closed_loop.py` | 通过，退出码 0 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

该记录不替代 EPE 运行生成的版本化 Evidence，也不证明宿主写入隔离或远程 CI 已运行。前后采样无法发现中间被修改后恢复的策略。
