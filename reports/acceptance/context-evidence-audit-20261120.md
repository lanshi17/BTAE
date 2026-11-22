# 上下文证据状态：本地验证记录

- 目标：MOD-004、MOD-006、MOD-008；时间：2026-11-20 09:49 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树有未提交修改。
- 输入 SHA-256：
  - `src/epe/cli.py`：`c1f49889517e22868584e955f5c043a1bd7ea27f311675be55c699fa2e10c72c`
  - `src/epe/context/resolver.py`：`82188b0e0c2a2fa0c3581e8cffe6dd84cad0a09973e8ac1a0b8ef184f1ed08fb`
  - `docs/modules/context/README.md`：`4903186ba538686f7891f793d35d4441391384adacb3d399453be41b69523242`
  - `tests/acceptance/test_ac12_closed_loop.py`：`efa7ec50e571afb7b9bc6f488cc23db07e3cb4ad2613d4067ad952878932134e`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

真实 CLI 测试覆盖审计失败降级、非对象 JSON 的故障响应，以及证据到期后的缓存失效。本地审计仍不是外部不可变审计；此记录不替代 EPE 版本化 Evidence。
