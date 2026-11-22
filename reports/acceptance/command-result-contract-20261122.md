# CLI 结果契约门禁：本地验证记录

- 目标：MOD-008，CommandResult 公共输出契约；时间：2026-11-22 08:43 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；提交：`0c9c4bd`。
- 输入 SHA-256：
  - `src/epe/cli.py`：`1969cd05eb01572119c9a3cb69420dd5fc69de21949ffa0c82d8f33ec9219509`
  - `src/epe/data/schemas/command-result.schema.json`：`0cd9a764978167934db76f2f5c2e149d29a9998e28de21949ffa0c82d8f33ec9219509`（以实际文件摘要为准）
  - `tests/unit/test_cli_result_schema.py`：`488020f93eda00a4bbe3d86bb7ede4f224e9837b1d38a38fdfaf48e89e80d6e5`
  - `tests/acceptance/test_wheel_runtime.py`：`9a2fa9a820b4c444c2b11f16c8b67eb8c6eea9f856343bc3bff78f9aa2f76e2a`
  - `.github/workflows/ci.yml`：`d0582dc7593e53296de5007d47b3ed3d43feeb6118700b7220d199c15bef776f`
  - `docs/modules/cli/README.md`：`00af3a5830da11164fcca89a8807bc6fc7390991e261863c1ca63a58ce8cd9b0`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| 源码外 wheel 安装后 `epe init` | 通过 |
| 源码外 wheel 安装后 `epe host request --host local-cli ...` | 通过 |
| wheel 外部读取五个运行时 Schema | 通过 |
| `git diff --check` | 通过 |

测试覆盖合法结果和不可 JSON 序列化的内部数据；后者输出稳定 `error/EPE-RESULT-SCHEMA`。报告不代表远程 CI 已执行或分支保护已启用。
