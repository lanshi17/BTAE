# 证据读取故障门禁：本地验证记录

- 目标：MOD-006，AC-08 / AC-12；时间：2026-11-20 09:20 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树包含未提交修改。
- 输入 SHA-256：
  - `src/epe/verification/runner.py`：`34ed792928c68107eb16674a5222c6923a88a7b5957e4e0bbda79d8cb5acfd44`
  - `src/epe/cli.py`：`afdcce98c4e5ac1494cc7ffee94ae3c7046b5afb0d253e64d51508f6d9539dd7`
  - `docs/modules/verification/README.md`：`1cc52518b407a0b3e3f8e8477659b68e459452a899e956bfc4aa3f4d13a4a799`
  - `tests/acceptance/test_ac12_closed_loop.py`：`5a9924ad4dfefbf08ed671ef65df859ca6d0e05ba93deb646029831b1f692724`
  - `tests/acceptance/test_mvp_scenarios.py`：`b5e7bba32276b543302cf72e8607eb7329719a5558304cb08081044d6ab2fa14`

| 命令 | 实际结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

完整回归在更新缺失证据的故障退出码预期前曾有一项失败，更新后重跑通过。测试覆盖保留旧通过记录时，最新失败记录损坏或缺失的情形；整个运行目录被删除仍无法通过目录扫描发现。此记录不替代 EPE 版本化 Evidence。
