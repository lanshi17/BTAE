# 运行时 Schema 发布：本地验证记录

- 目标：MOD-008 / MOD-009，源码外 wheel 的机器契约可用性；时间：2026-11-22 08:50 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；提交：`fc4f094`。
- 发布包现包含 14 个 Schema：approval、agent-request、agent-response、changeset-baseline、changeset、command-result、contract、entity、evidence、policy、project-config、relation、task、workflow。
- 关键测试输入：`tests/acceptance/test_wheel_runtime.py` SHA-256 `cd296fab1232a18df6db6387a794103f11d419729c61530a758bb3f66c198b6b`。

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/acceptance/test_wheel_runtime.py tests/acceptance/test_policy_validate.py` | 通过，退出码 0 |
| `python -m pip wheel . --no-deps` + 新虚拟环境安装 | 通过 |
| 新虚拟环境读取 14 个 `epe.data.schemas` 文件 | 通过 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

该记录证明包内资源可读取，不证明远程 CI 已执行或远程合并保护已启用。
