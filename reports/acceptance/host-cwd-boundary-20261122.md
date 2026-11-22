# Hermes bridge 工作目录边界：本地验证记录

- 目标：MOD-009，Host adapter 运行上下文；时间：2026-11-22 08:32 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；提交：`51cbfc8`。
- 输入 SHA-256：
  - `src/epe/adapters/hosts/hermes.py`：`5a3f79c05bf48a7a8a3d058ce8692f9e47b3f93f794dce222963739ec3306246`
  - `src/epe/cli.py`：`812665a5a23b3a6213c2d30cd8de569b3fd9b922e205ba85ee647ef5c70dc51e`
  - `tests/integration/test_hermes_adapter.py`：`9b44721fdcf862dbf4b58ea3e9e57e04fb6cb602890c3cdc538d99f163222db7`
  - `docs/modules/adapters/host-capability-matrix.md`：`b809764cbd8752b1d300c994e77c93f3f1bb8d1bfbd00d2da8b999916943da18`
  - `docs/contracts/agent-protocol.md`：`8a5689e99387b613e41597514d0cf6c0b528f7d5665936864ba448a56b3dec1a`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

Hermes 模拟子进程通过 `os.getcwd()` 返回 cwd，测试确认 adapter 使用显式仓库目录；CLI 将 `--root` 解析结果传入 adapter。测试使用模拟桥接，不证明真实 Hermes 权限或宿主隔离。
