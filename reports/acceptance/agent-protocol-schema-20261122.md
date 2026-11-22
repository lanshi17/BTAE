# Agent 协议机器契约同步：本地验证记录

- 目标：MOD-009，AgentRequest / AgentResponse 公共契约；时间：2026-11-22 06:47 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树包含此前未提交修改。
- 输入 SHA-256：
  - `engineering/schemas/agent-request.schema.json`：`4ca6bd9ac4e6a2758c9275a7bd76218e5fce1338eeb001716d0ac389da1320ba`
  - `engineering/schemas/agent-response.schema.json`：`640b7f68945c3178d867373481a9abc42223441206f184feb6b1ce3e23e2cae8`
  - `src/epe/adapters/protocol.py`：`ba235f2dccfd4ab26aac4c7eafcfd0eac0aad4ccd6201518c6b8212113cb524b`
  - `tests/unit/test_protocol.py`：`54e46d23e508ad4f927a3f9acdec654e2fbcb54de4dbca12d19e48ba7d80c979`
  - `docs/contracts/agent-protocol.md`：`cd6df087c62ac548a4995c9155e440978dfa057508743120fb2bd19518722f5f`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/unit/test_protocol.py tests/unit/test_host_adapter.py tests/integration/test_hermes_adapter.py tests/acceptance/test_host_capabilities_cli.py` | 通过，退出码 0 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `jsonschema.Draft202012Validator.check_schema`（两个 Agent Schema） | 通过 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

请求 Schema 现在要求协议版本和 `trusted_identity.source`；响应 Schema 允许实现实际返回的 `unsupported` 决策。测试将值对象序列化为 JSON 后按机器 Schema 校验，避免 Python tuple 与 JSON array 的表示差异。真实 Hermes 宿主仍未接入或验收。
