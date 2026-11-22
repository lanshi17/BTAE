# 验证证据审计绑定：本地验证记录

- 目标：MOD-006、MOD-007、MOD-008，AC-08 / AC-12；时间：2026-11-20 09:36 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树有未提交修改。
- 输入 SHA-256：
  - `src/epe/cli.py`：`8197321ea49f5e16ce60dfcd8e3bf738d157a48fcb0a916ee918468c63abdaf3`
  - `src/epe/governance/baseline.py`：`5356ef9cadce80f9682dc3dfc0efaefa4b470e7ffc4e5e9990a908c99a68f319`
  - `docs/modules/verification/README.md`：`0e8205da6a14bdae7933549266df555398ce168a3f58c5b1826aabb581ad9dfb`
  - `docs/modules/governance/README.md`：`fab74b8e5e79cfe97e770327c9c8d405cb2ca482e3c1fd50f0bea3276372f441`
  - `tests/acceptance/test_ac12_closed_loop.py`：`f660f192a8261676e2c7becc296b7eed0c3fbaf52387c1d9e34394d7f42a098c`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0；治理文档说明在测试后补充 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0；文档补充后重建 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

端到端测试覆盖审计丢失导致旧证据 unknown、已登记失败运行的目录删除导致故障，以及正常闭环。审计与证据发布非原子事务；本地链不具备外部不可变性。此记录不替代 EPE 版本化 Evidence。
