# wheel 源码外回归（2026-11-23）

- 代码基线：`8aad457414da9e9330996a4ebd7e3ab90677595bc`。
- 在隔离临时目录执行 `python -m pip wheel . --no-deps`，随后创建新 virtualenv，仅安装生成 wheel。
- 从 `/tmp`（源码目录外）运行隔离环境的 `epe --format json host capabilities`，退出码 0，返回单一合法 `CommandResult`；运行时 Schema 可从 wheel 读取，Hermes 仍为 `unsupported-unintegrated`，未被包装安装误报为已集成。
- wheel SHA-256：`f359e28478d94723980b78d1c4b9392481839d62fc0a44e76ca98fda2a303ef7`。

该检查证明发布包包含当前运行时 Schema 和 CLI 入口，不证明 wheel 环境具备 Hermes 身份、工具权限、写入隔离或远程审计。
