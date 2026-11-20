# TASK-artifact-store：本地不可覆盖产物存储

- 类型：Feature；高风险；MOD-009 ArtifactStorePort 与 MOD-006 验证日志/摘要写入；保护现有改动。
- 依据：adapters §3/§5、verification §5、WP-08 T4。当前只有空端口；runner 直接写日志，未共享路径与原子性约束。
- 设计：新增本地 `ArtifactStore`，以仓库根为信任边界，拒绝绝对路径、`..`、反斜杠及符号链接父/目标；同名产物不覆盖。通过安全目录描述符遍历、同目录临时文件、fsync 和硬链接原子发布完整内容，返回仓库相对路径和 SHA-256。runner 用它写日志与测试摘要；Evidence JSON 仍最后原子写入。外部生成的配置产物只读取摘要，不由 ArtifactStore 接管。
- 验收：写入得到正确摘要；重复写冲突；越界/符号链接拒绝；并发写只有一个胜出且产物完整；runner 日志/摘要改用端口实现。
- 限制：本实现依赖 POSIX dir_fd/O_NOFOLLOW/hardlink 语义；网络文件系统和 Windows 尚未声明支持；外部 expected artifact 与本地 run bundle 仍不属于同一跨路径事务。状态 draft。

- 本地验证：定向覆盖测试 19 passed，ArtifactStore 覆盖率 85%；完整测试 127 passed；`git diff --check` 通过。记录见 `reports/evaluations/artifact-store.json`。

- 本轮结果：新增 `publish_bundle`，验证日志、测试摘要和 Evidence 在 staging 目录完成后一次性发布；失败不留下最终 run 目录。定向 22 项、全量 170 项通过，证据见 `reports/evaluations/artifact-bundle.json`。
