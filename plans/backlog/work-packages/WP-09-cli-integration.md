# WP-09：统一 CLI 与完整应用链路

**状态：** in_progress · **里程碑：** M2 · **实施：** in_progress
**负责模块：** [cli](../../../docs/modules/cli/README.md) 牵头，装配全部 MVP 模块
**前置：** WP-05、WP-06、WP-07、WP-08

## 1. 目标

在组合根装配真实服务与端口，交付 SPEC 首批命令的统一 JSON/text 输出与退出码；跑通单任务从登记设计到真实验证与治理决定的主路径，以及主要失败诊断路径。

## 2. 命令交付清单

| 命令 | 本包要求 |
| --- | --- |
| `epe init` | 创建缺失模板/配置；冲突不覆盖（AC-01） |
| `epe inspect` | 只读范围与状态 |
| `epe task create/classify` | 登记与缺失项提示 |
| `epe design validate` | 只读校验 |
| `epe design approve --record` | 导入可信记录，非自授权 |
| `epe mapping validate` | 真实映射检查 |
| `epe graph build` | 原子发布快照 |
| `epe architecture validate` | 静态规则 |
| `epe verify` | 执行并写 Evidence |
| `epe sync` | 仅派生视图 |
| `epe check` | 聚合已有事实，**不**偷跑测试 |
| `context resolve` / `impact analyze` / `design create` | 已提供本地基础实现；质量评测、外部语义后端和高级宿主能力仍 deferred |

## 3. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 组合根：注入 adapters，禁止业务包反向依赖 cli |
| T2 | 统一 Result Schema、stdout JSON / stderr 日志 |
| T3 | 退出码表接线（D-11） |
| T4 | 逐命令接线与帮助文本 |
| T5 | 主路径集成：task → design → mapping → graph → architecture → verify → check |
| T6 | 失败路径：阻断、故障、冲突、unsupported 均有诊断 code |
| T7 | 确认命令不覆盖权威工件（除明示审计写入） |

## 4. 拟议路径

```text
src/epe/cli/
  main.py
  commands/
  composition.py
  render.py
tests/integration/cli/
tests/acceptance/mvp_happy_path/
```

## 5. 验收映射

AC-01、AC-09；串联 AC-02–08、11 的命令入口；完整 AC-12 在 WP-10 强化。

## 6. 完成门槛

- [ ] SPEC §8 首批命令行为与退出码一致
- [ ] `check` 在无新 verify 时不启动测试进程
- [ ] unsupported 不返回空成功
- [ ] 至少一条真实端到端成功路径 + 一条阻断路径有执行记录
