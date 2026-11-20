# WP-11：CI、使用文档与 MVP 发布

**状态：** planned · **里程碑：** M3 / V0.2 发布 · **实施：** not_started  
**负责模块：** cli / adapters；维护者配置远程门禁  
**前置：** WP-10

## 1. 目标

将模型/依赖/架构/契约/验收测试纳入 CI；提供真实命令与故障恢复文档；形成 MVP 发布清单与试点基线。本计划**不**等同于已在远程仓库启用保护规则。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | CI 工作流：单元、契约、架构导入、acceptance |
| T2 | 产物上传策略与保留（对齐 D-07） |
| T3 | 文档：安装、首日闭环、常见阻断与恢复 |
| T4 | 明确“检查可用”vs“合并已强制”两种部署状态 |
| T5 | MVP 发布清单对照 PRD KR-01–KR-05 |
| T6 | 试点基线：仓库规模、耗时、失败类型（实测，不编造） |
| T7 | 若需设置受保护分支/必需检查：单独授权变更，记录操作者与时间 |

## 3. 拟议路径

```text
.github/workflows/epe-ci.yml   # 或项目选定 CI 系统
docs/standards/user-guide-mvp.md
docs/standards/runbook-recovery.md
plans/backlog/mvp-release-checklist.md  # 发布时填写
```

## 4. PRD KR 对照（发布时实测勾选）

| KR | 含义（见 PRD） | 证据形式 |
| --- | --- | --- |
| KR-01–05 | 以 PRD 原文为准 | CI 日志 + acceptance 报告 + 试点记录 |

## 5. 完成门槛

- [ ] CI 与本地同一结果模型（AC-09 同源）
- [ ] 未配置远程保护时文档明确“仅提供检查”
- [ ] 发布清单无未关闭的 blocking 项
- [ ] 不把本 WP 文档当作远程已部署证明
