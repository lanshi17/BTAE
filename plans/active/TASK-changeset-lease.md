# TASK-changeset-lease：本地 ChangeSet 租约

- 类型：Feature；风险：high；涉及 MOD-007、MOD-008、MOD-009；范围为 EPE 自身进程间协调，不宣称操作系统锁或宿主隔离。
- 设计依据：治理模块关于 V1.0 租约/续期/恢复的约束。租约文件位于 configured ChangeSet 目录，使用 EPE 写锁和 O_EXCL/原子替换；记录 `schema_version`、`changeset_id`、`lease_id`、owner、pid、acquired_at、expires_at 与 ChangeSet revision。
- CLI：`epe changeset lease acquire ID --owner OWNER --ttl SECONDS`、`renew`、`release`、`inspect`。获取要求 ChangeSet 为 active、owner 匹配且无未过期租约；过期租约可在 EPE 写锁内回收。续期/释放要求 owner 与 lease_id 匹配，过期或 revision 变化拒绝；释放幂等地报告已释放/不存在。
- 验收：并发获取只有一个成功；错误 owner/lease ID、过期、revision 变化、非法 TTL 和损坏记录均失败；过期租约可恢复；状态和审计不因 inspect 改变。
- 限制：外部进程可忽略租约或修改记录，时钟异常和进程崩溃只能通过 TTL 恢复；不提供身份认证、跨机器一致性、文件系统写保护或多仓库协调。设计状态 draft。

## 本轮结果

- 新增 `epe changeset lease acquire|renew|release|inspect` 与本地租约存储；获取使用 EPE 写锁和独占创建，过期记录可回收，续期绑定 owner、lease ID 和 ChangeSet revision。
- 单元及真实 CLI 生命周期测试覆盖冲突、错误身份、revision 变化、TTL 过期恢复和只读 inspect。
- acquire/renew/release 追加带 lease ID、revision 和记录摘要的 hash-chain 审计事件；inspect 不写入状态或审计。
- 独立 CLI 进程并发获取时，失败方返回统一 `blocked`/`EPE-WRITE-CONFLICT` JSON，不泄漏未处理异常。
