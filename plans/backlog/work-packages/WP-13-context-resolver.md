# WP-13：分级上下文与混合检索

**状态：** in_progress · **里程碑：** M4 / V0.3 · **实施：** in_progress
**负责模块：** [context](../../../docs/modules/context/README.md)、graph、cli
**前置：** WP-12

质量、上下文体积和成本的评测协议见[研究评测计划](../research-evaluation.md)；未取得独立样本前不报告收益比例。

## 1. 目标

实现 ID / 图邻接 / 关键词检索与 C0–C3 分级装配及预算控制；区分当前事实、历史、推断；缓存随设计/批准/Evidence 变化失效。无外部语义服务时基础能力仍可运行。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 冻结 ContextBundle、omissions、预算与排序解释字段 |
| T2 | 检索顺序：显式 ID → 图邻接 → 关键词 →（可选）BM25/向量 |
| T3 | C0 必保（任务直接实体、适用批准、有效策略）；不可静默裁掉 |
| T4 | 来源与可信度呈现；推断不可扮成已验证 |
| T5 | 缓存键含设计修订、批准集、Evidence 有效性视图版本 |
| T6 | `epe context resolve`；任务相关性样本与人工评测记录 |
| T7 | 后端选择：先可运行默认；向量依赖数据与成本决策后再加 |

## 3. 拟议路径

```text
src/epe/context/resolve.py
src/epe/context/budget.py
src/epe/context/retrieve.py
tests/unit/context/
tests/fixtures/context_tasks/
```

## 4. 分级（与模块文档对齐，实施前复核）

| 级 | 典型内容 | 裁剪规则 |
| --- | --- | --- |
| C0 | 直接目标实体、有效批准、门禁策略 | 不可因预算删除 |
| C1 | 一跳依赖与契约 | 可按相关度裁 |
| C2 | 邻接测试/Evidence 摘要 | 可裁，须记 omissions |
| C3 | 背景/历史/推断 | 最先裁；必须标类型 |

## 5. 完成门槛

- [ ] 无向量服务时 C0–关键词路径可用
- [ ] C0 静默裁剪测试失败（即有防护断言）
- [ ] 缓存失效场景有测试
- [ ] 质量与成本试点记录存在；不预设 Token 节省比例
