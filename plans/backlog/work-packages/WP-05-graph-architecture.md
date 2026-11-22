# WP-05：基础图、架构规则与快照发布

**状态：** in_progress · **里程碑：** M1 · **实施：** in_progress
**负责模块：** [graph](../../../docs/modules/graph/README.md)、verification、adapters
**前置：** WP-03、WP-04 · **下游：** WP-08、WP-09、WP-12

## 1. 目标

由注册快照与代码事实构建确定性图；提供邻接/循环查询；执行禁止依赖与模块循环的架构检查；按 WP-01 的 generation+指针方案原子发布，删除缓存可重建。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | Graph Builder：显式边 + 静态导入事实；冲突不按 confidence 静默覆盖 |
| T2 | 模块归属聚合依赖；归属歧义诊断 |
| T3 | Query：正反邻接、路径、`dependency_cycles` |
| T4 | Architecture Validator：消费有效规则，输出 pass/fail/unknown |
| T5 | SnapshotStore 端口 + adapters 实现：临时 generation、锁、原子切换 |
| T6 | incomplete / 悬空边拒绝发布完整快照；失败保留旧指针并标过期 |
| T7 | 确定性：打乱输入顺序内容摘要不变；时间戳不参与内容指纹 |
| T8 | 并发第二写者 → 冲突（退出码语义在 CLI 侧 WP-09 接线） |

## 3. 拟议路径

```text
src/epe/graph/builder.py
src/epe/graph/query.py
src/epe/graph/snapshot.py
src/epe/verification/architecture.py
src/epe/adapters/snapshot_store.py
.engineering/          # 仅派生；格式见 WP-01 D-08
  current -> generations/<id>/
tests/unit/graph/
tests/integration/graph_snapshot/
tests/fixtures/architecture_cases/
```

## 4. 架构检查语义

| 情况 | 报告 |
| --- | --- |
| 静态边违反禁止导入 | fail + 路径/来源 |
| 模块依赖环 | fail + 环路径 |
| 仅动态未知、静态无违规 | unknown 或带盲区说明的受限 pass（按策略）；**不能**声称全局无违规 |
| 例外 ADR 过期/范围不符 | 例外无效，按原规则判定 |

## 5. 验收映射

AC-04（静态禁止依赖与环）；AC-10 的重建与基础并发；明确 **不** 交付 impact analyze（unsupported 留给 WP-09/12）。

## 6. 完成门槛

- [ ] 删除 `.engineering/` 后同输入重建内容一致
- [ ] 从不发布半张图；读者只见完整 generation
- [ ] graph 包仅依赖 core；应用层注入解析产物
- [ ] 盲区不会被解释为“无架构问题”
