# 本地 MVP 完成审计（WP-01–WP-14）

执行时间：2026-11-22 · 基线：`8695d1a`

这份审计把“本地实现已存在”和“完整目标已关闭”分开。状态依据当前文件、真实命令和测试结果；没有把设计草案、模型自述或固定测试夹具当作外部能力证明。

| 工作包 | 当前可证明范围 | 证据 | 尚未关闭的门槛 |
| --- | --- | --- | --- |
| WP-01 | Schema、模板、状态/关系/结果契约已入库；HostPort 机器契约新增 | `engineering/schemas/`、`engineering/templates/`、`docs/contracts/host-port.md`、`engineering/contracts/host-port.yaml` | 适用的人类评审、正式批准和迁移记录 |
| WP-02 | 可安装包、核心模型、Registry、端口、CLI inspect 已实现；核心类设计文档与本地验证状态已同步；Task Schema 与 Workflow 字段保持同步 | `pyproject.toml`、`docs/classes/`、`tests/unit/test_core.py`、`tests/acceptance/test_cli.py`、`engineering/schemas/task.schema.json` | 核心设计从 draft 进入批准流程 |
| WP-03 | Markdown/YAML/Python 批量解析、来源和不完整状态已测试 | `src/epe/parsers/`、`tests/unit/test_parsers.py` | 多语言解析与正式评审 |
| WP-04 | AST 符号/导入、映射正反例和动态盲区已测试 | `tests/acceptance/test_ac03_mapping_cli.py`、`tests/unit/test_parsers.py` | 运行时动态依赖无法由静态 AST 证明 |
| WP-05 | 确定性图、模块覆盖、架构规则、generation 原子发布和冲突保护已测试；最终快照 321 节点 / 443 边 | `tests/integration/test_graph_generations.py`、`tests/acceptance/test_ac10_graph_publication_cli.py` | 断电持久性和完整平台矩阵 |
| WP-06 | 设计指纹、契约校验（含仓库内 `$ref` 解析）、可信签名批准和撤销路径已测试 | `tests/integration/test_approval_signatures.py`、`tests/unit/test_contract_validation.py`、`src/epe/design/manager.py` | 远程不可变审批审计、人类评审 |
| WP-07 | Task/ChangeSet 生命周期、风险门禁、范围、Evidence、配置化 Workflow 要求、分类缺项和 ChangeSet 契约反例已测试 | `tests/unit/test_finalize_gate.py`、`tests/integration/test_changeset_baseline.py`、`tests/acceptance/test_task_workflow.py` | 宿主级权限强制 |
| WP-08 | 真实子进程、超时/取消、JUnit 结果、Evidence 有效性和篡改检测已测试 | `tests/integration/test_process_lifecycle.py`、`tests/integration/test_evidence_snapshot_integrity.py` | 远程产物信任与非 POSIX 强制语义 |
| WP-09 | 首批 CLI、统一结果/退出码和真实闭环已实现 | `src/epe/cli.py`、`tests/acceptance/test_ac12_closed_loop.py` | 复杂宿主编排仍不在本地 CLI 权限边界内 |
| WP-10 | AC-01–AC-12 均有自动化入口；全量本机回归 254 项通过；存在真实进程/锁/产物故障注入 | `reports/evaluations/ac-coverage-matrix.json`、`reports/acceptance/local-regression-20261122.md` | 完整平台矩阵与所有故障恢复场景的独立记录 |
| WP-11 | CI 工作流、wheel 隔离检查、上手/恢复文档和发布限制已入库 | `.github/workflows/ci.yml`、`docs/standards/`、`plans/backlog/mvp-release-checklist.md` | 远程分支保护和必需检查尚未由仓库证明 |
| WP-12 | 双向影响、历史快照、预算截断和增量/全量等价已实现并回归 | `tests/unit/test_impact_propagation.py`、`tests/integration/test_context_incremental.py` | 独立真实标注集、精确率/召回率和成本基线 |
| WP-13 | C0–C2 ID/图/关键词上下文、来源标记和缓存失效已实现并测试 | `src/epe/context/resolver.py`、`tests/unit/test_v03.py`、`tests/acceptance/test_context_cache_cli.py` | 独立相关性评测、Token/成本试点、BM25/向量后端 |
| WP-14 | HostPort v1、Hermes argv bridge、能力握手和明确拒绝路径已实现 | `docs/contracts/host-port.md`、`src/epe/adapters/hosts/hermes.py`、`tests/integration/test_hermes_adapter.py` | 真实 Hermes 身份/隔离/取消实测、四类宿主工作流、多 Agent 协作和长期消融 |

## 本轮复核命令

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=src pytest -q` | 254 项通过 |
| `PYTHONPATH=src python -m epe.cli --format json policy validate` | `passed` |
| `PYTHONPATH=src python -m epe.cli --format json design validate CONTRACT-HOST-PORT-001` | `passed` |
| `PYTHONPATH=src python -m epe.cli --format json graph build` | `passed`，321 节点 / 443 边 |
| `PYTHONPATH=src python -m epe.cli --format json architecture validate` | `passed` |
| `git diff --check` | 通过 |

因此当前仓库可以准确称为“本地 MVP 检查能力已实现并有回归证据”；不能据此关闭真实宿主、远程治理或方法收益验证。
