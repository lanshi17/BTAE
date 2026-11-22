# 影响传播置信度：本地验证记录

- 目标：MOD-003，PRD-010 部分场景；时间：2026-11-20 09:24 UTC 附近。
- 环境：Linux，Python 3.14.4，pytest 9.1.1；Git 基线 `caf7831`，工作树含未提交修改。
- 输入 SHA-256：
  - `src/epe/graph/builder.py`：`9a874d26e2b8925de47380bde2c40dcdcc3a884d6f84273d76b7419031851b38`
  - `docs/modules/graph/README.md`：`b815efb985c7a7d5e9a373ac9f90c13af04b553586d1d509d9903e4a235323e9`
  - `tests/unit/test_impact_propagation.py`：`8e0a044fda3693da6b8a091f8a219d4d0592082d86ff3e672f75a26d32071645`
  - `tests/benchmarks/impact_labeled/cases.json`：`b030b3a7459f19c3b67aeffb52694acbc447c8b55601087e35ce5134ee202c81`
  - `tests/benchmarks/impact_labeled/test_labeled_cases.py`：`2e78272c8cecf540f55f839397d8fd489ddaad63df2b32a0d4fb06f8b5c11de1`

| 命令 | 实际结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q tests/unit/test_impact_propagation.py tests/benchmarks/impact_labeled/test_labeled_cases.py` | 通过，退出码 0 |
| `PYTHONPATH=src pytest -q` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | 通过，退出码 0 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | 通过，退出码 0 |
| `git diff --check` | 通过，退出码 0 |

三个合成场景的预期结果均匹配；这不是独立真实项目评测，不能据此报告一般化精确率、召回率或方法收益，也不替代 PRD-010 的完整验收。
