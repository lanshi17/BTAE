# WP-14：宿主集成、完整工作流与持续演进

**状态：** planned · **里程碑：** M5 / V1.0 · **实施：** not_started  
**负责模块：** adapters、governance、context、verification  
**前置：** WP-13  
**说明：** Hermes 优先，但核心协议保持宿主无关。权限隔离以实测可强制边界为准，不把“可绕过 CLI”宣称为安全边界。

## 1. 目标

冻结 HostPort 请求/响应；接入优先宿主并给出能力矩阵；补全四类工作流执行与协作冲突处理；建立预期架构 vs 发现架构的协调与长期实验框架（PRD-011/012）。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 冻结 HostPort：request_id、Task/ChangeSet、设计指纹、写入范围、决策响应 |
| T2 | Hermes 适配；不支持能力明确拒绝 |
| T3 | 可选第二宿主；能力矩阵分列 |
| T4 | 四类工作流端到端编排（非仅登记） |
| T5 | 多 Agent / 共享契约变更协调；若实现锁：租约与恢复实测 |
| T6 | 架构差异报告与 ADR 协调流程接线 |
| T7 | 长期试点与消融实验设计落地（对照 A/B/C/D，见路线图 §5） |
| T8 | 专属验收：宿主权限、拒绝路径、锁恢复、架构差异可追溯 |

## 3. 拟议路径

```text
src/epe/adapters/hosts/base.py
src/epe/adapters/hosts/hermes.py
docs/contracts/host-port.md
docs/modules/adapters/host-capability-matrix.md
tests/integration/hosts/
plans/backlog/research-evaluation.md  # 实验计划，非产品完成证明
```

## 4. 能力矩阵列（示例）

| 能力 | Hermes | 其他 | 无宿主 CLI |
| --- | --- | --- | --- |
| 可信身份 | 待测 | — | 维护者配置 |
| 写入隔离 | 待测 | — | **无**（仅检查） |
| 取消/超时 | 待测 | — | 进程组 |
| 不支持操作 | 必须拒绝 | 必须拒绝 | unsupported |

“待测”在实测前不得勾选为已支持。

## 5. 完成门槛

- [ ] HostPort 版本化且有正反契约测试
- [ ] 能力矩阵无夸大隔离声明
- [ ] 四类工作流有真实执行证据
- [ ] 方法收益对照/消融有独立报告入口；产品发布不依赖“已证明优于 SDD”
