# 证据有效期：本地验证记录

- 目标：MOD-006、SPEC-BTAE §4；时间：2026-11-20 09:43 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树有未提交修改。
- 关键输入 SHA-256：
  - `src/epe/verification/runner.py`：`f35663ab5bef232f1cdfe666bcbc7add45689dca3a3cc1245484f7b5df263a24`
  - `engineering/schemas/policy.schema.json`：`b6431e6b8cd12b72554f350f420db3edd63c0b0c304c3200fae4b150c3d1b817`
  - `src/epe/data/schemas/policy.schema.json`：`016a91eaa6b287a89aa4719a6942b8ac491fb181f09258cfe9d4ff6973d8fd7e`
  - `docs/intent/requirements/SPEC-BTAE.md`：`b4c47ff815cdeaceea2abe923125d4c793c226796a1ec94a11efd268d7a6ef04`
  - `docs/modules/verification/README.md`：`7ad0cf88661575b6defae89f09fc83d05e69f700d9eb9c6fcfd6845cf24e34b5`
  - `tests/acceptance/test_ac12_closed_loop.py`：`f2b289ee0797d09eb304f742ee10e363d9a89a24d67c311f861ac6a63f9aa6dd`
  - `tests/integration/test_evidence_snapshot_integrity.py`：`db0614825b41781dba6fc821256b6cc71cdd03692a8eef6216f0b6f661c22f9c`

| 实际命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| 对两个策略 Schema 解析 JSON，忽略可选 title 后比较 | 约束一致；字节比较因现有 title 差异不相等 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

集成测试覆盖期限边界、未来时间、无时区和非法策略；端到端测试实际等待后确认过期证据阻断完成。此记录不替代 EPE 版本化 Evidence。
