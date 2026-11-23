# 远程分支治理复核记录（2026-11-23）

- 仓库：`lanshi17/BTAE`
- 目标分支：`master`
- 配置时间：2026-11-23 03:01 UTC
- 配置接口：GitHub Branch Protection API

## 已应用规则

| 规则 | 实际值 |
| --- | --- |
| 必需状态检查 | `checks` |
| 必需状态检查严格更新 | `true` |
| 必需 PR 审查 | 1 次 |
| 过期审查自动失效 | `true` |
| 管理员也受保护规则约束 | `true` |
| 强制推送 | 禁止 |
| 删除分支 | 禁止 |

复核命令：

```bash
gh api repos/lanshi17/BTAE/branches/master
gh api repos/lanshi17/BTAE/branches/master/protection
```

API 返回 `protected: true`，并返回上述 required status check、审查、管理员、强推和删除设置。该记录证明 GitHub 远程规则已配置；它不替代 PR 审查本身，也不证明真实 Hermes 权限或方法收益实验已经完成。
