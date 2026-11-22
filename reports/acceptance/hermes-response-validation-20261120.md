# Hermes 桥接响应校验：本地执行记录

- 目标：MOD-009，宿主协议输入边界；时间：2026-11-20 09:13 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树包含未提交变更。
- 输入 SHA-256：
  - `src/epe/adapters/hosts/hermes.py`：`7af45a7f4cfa684928c96ae3fa708aeb30797a8a5c5619d1dc5d9d56560db192`
  - `src/epe/adapters/protocol.py`：`a11382bc07c8446daad037f2402552316b821f32ed0d694526d65e4c3acf8d54`
  - `docs/contracts/agent-protocol.md`：`e6bd9574e85db4b28c5795d9d4ed7b659f824db4bb68389a93308ca0bc8c4172`
  - `tests/integration/test_hermes_adapter.py`：`19fff4d70a11634ffb809f824a5e5eb420e65f5bc56fd51faf8872071b76ab7c`

| 命令 | 实际结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/integration/test_hermes_adapter.py tests/acceptance/test_host_capabilities_cli.py` | 通过，退出码 0 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

测试使用本地模拟子进程，并非真实 Hermes 宿主；结果不证明宿主身份、隔离能力或端到端集成。该记录不替代 EPE 版本化 Evidence。
