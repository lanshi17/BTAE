# WP-12：双向影响分析与增量图

**状态：** planned · **里程碑：** M4 / V0.3 · **实施：** not_started  
**负责模块：** graph、parsers、adapters  
**前置：** WP-11 · **下游：** WP-13  
**说明：** 进入实施前应单独立项补充专属验收（PRD-010），**不得**冒用 AC-01–12 声称高级影响能力已验收。

## 1. 目标

定义关系传播方向与停止规则；支持设计/代码/删除/移动的影响报告；增量重解析与全量重建内容等价；旧索引版本不得得出“当前无影响”。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 冻结传播矩阵：`realizes` 正反、`depends_on` 消费者反向、verified_by/evidenced_by 等 |
| T2 | ImpactReport：路径、确定/候选、截断标志、原因 |
| T3 | 删除/移动：必须基于变更前快照追溯消费者 |
| T4 | Incremental Planner：重解析集合；Schema/解析器/包根变化回退全量 |
| T5 | 增量 vs 全量内容等价测试 |
| T6 | `epe impact analyze` 接线；预算耗尽 → truncated |
| T7 | 独立真值标注集；记录精确率/召回与成本（研究指标，非门禁冒充） |

## 3. 拟议路径

```text
src/epe/graph/impact.py
src/epe/graph/incremental.py
.engineering/generations/<id>/impact-index.json  # 派生
tests/unit/graph/test_impact.py
tests/benchmarks/impact_labeled/
```

## 4. 传播示意（实施前以冻结矩阵为准）

```text
代码变更 → realizes 反向 → 设计实体 → depends_on 反向消费者
                                      → verified_by / evidenced_by
设计变更 → realizes 正向 → 实现符号/文件
```

推断边不得单独升级为“确定影响”。

## 5. 完成门槛

- [ ] 专属验收场景文档已批准或至少 reviewed
- [ ] 增量≡全量有自动断言
- [ ] 截断与未知范围显式表达
- [ ] 试点指标入库，不预设优于基线
