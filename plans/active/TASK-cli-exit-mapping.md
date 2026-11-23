# TASK-cli-exit-mapping：CLI 退出码完整映射

- 类型：Bugfix；中风险；MOD-008 CLI；范围退出码映射和回归测试；不改变领域状态。
- 依据：SPEC §8/§9、cli §4。当前 Exit Mapper 只把部分 Task/config code 映射为 2，路径符号链接、Task ChangeSet、Entity/ChangeSet 参数错误可能落到 3。
- 设计：维护稳定的参数/配置诊断前缀集合，覆盖配置缺失/类型/Schema、Task 字段、可识别的 ChangeSet 字段、路径越界/符号链接、策略参数和实体 ID；结果 status 仍保留 error/blocked/unsupported，退出码只按优先级映射。写冲突继续优先 5，执行故障 3，阻断 1，不把普通业务违规误归为参数错误。
- 验收：CLI init 符号链接、非法 Task ChangeSet、可识别的非法 Changeset ID、配置缺失分别返回 2；磁盘/ArtifactStore 故障返回 3；写锁冲突返回 5；unsupported 返回 4。
- 状态：draft。
- 本轮补充：策略 Schema/类型/读取错误、验证检查配置错误、任务 Schema 与未知字段错误统一映射为参数/配置退出码 2；普通门禁阻断、执行故障和写冲突的优先级保持不变。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，140 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/cli-exit-mapping.json`。
