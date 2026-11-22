# WP-08：检查运行器与 Evidence

**状态：** in_progress · **里程碑：** M2 · **实施：** in_progress
**负责模块：** verification、adapters
**前置：** WP-05、WP-07（授权上下文契约） · **下游：** WP-09、WP-10

## 1. 目标

将已授权配置转为 `ExecutionPlan`，经 ProcessPort 真实执行检查；采集前后 manifest；原子发布产物与不可变 Evidence；计算 validity。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | ExecutionPlan 模型：参数数组、cwd、超时、产物、解析器、配置版本 |
| T2 | TestRunner：启动进程组、捕获日志/退出码/收集数；超时杀进程组 |
| T3 | 结果分类：passed/failed/error/not_run（见 verification 模块表） |
| T4 | EvidenceManager：独立 Run ID；先产物后记录；失败也留痕 |
| T5 | validity：valid/stale/invalid/unknown（D-06/D-07） |
| T6 | 脱敏与环境允许列表；禁止保存密钥环境值 |
| T7 | 脏树/无提交仍可追溯；报告写入不进入源 manifest |
| T8 | 集成测试用可控小程序，不单靠 Mock 证明杀进程 |

## 3. 拟议路径

```text
src/epe/verification/runner.py
src/epe/verification/evidence.py
src/epe/verification/validity.py
src/epe/adapters/process.py
src/epe/adapters/artifact_store.py
reports/tests/
reports/runs/<RUN-ID>/
# Evidence 审计路径以 WP-01 为准
tests/unit/verification/
tests/integration/verification_run/
tests/fixtures/runner_programs/
```

## 4. 场景矩阵（必须真跑）

| 场景 | 执行结果 | validity 相关 |
| --- | --- | --- |
| 断言通过 | passed | valid（输入不变） |
| 断言失败 | failed | 可为 valid 诊断证据 |
| 零测试收集 | failed | 测试要求未满足 |
| 命令缺失 | error | — |
| 超时 | error/not_run（按是否启动） | 记录终止原因 |
| 执行中改输入 | 保留真实结果 | stale |
| 篡改产物摘要 | 保留原结果字段 | invalid |
| 环境不足 | 保留结果 | unknown |

## 5. 验收映射

AC-06、AC-07、AC-08；为 AC-12 提供真实 Evidence。

## 6. 完成门槛

- [ ] 未保存证据不能返回“留证成功”
- [ ] 参数必须来自授权配置数组，禁止 Task 文本拼 shell
- [ ] 进程组终止有集成实测
- [ ] Evidence 记录字段满足 SPEC §3.4
