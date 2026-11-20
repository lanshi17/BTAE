# TASK-design-fingerprint-declaration：设计声明指纹完整性

- 类型：Bugfix；高风险；MOD-005 设计 revision、批准适用性、测试和设计文档；保留其他工作。
- 依据：design §5、WP-06 T3/T6、WP-01 D-03。当前 revision 使用 `Entity.to_dict()` 与正文摘要，但 `Entity.raw` 中的 `extensions`/声明字段未参与摘要，声明变化可能复用旧审批。
- 设计：revision payload 同时绑定规范化正文 bytes、完整原始声明元数据（去除仅解析内部字段，不丢弃 `extensions`）、实体 ID/类型和引用契约摘要；算法版本升级为 v3，旧 v2 批准自然 stale。拒绝设计源符号链接和仓库外路径。批准导入/完成检查继续使用当前 revision。
- 验收：修改 extensions、映射、状态或引用契约后 revision 改变；旧批准被判 stale；批准导入不修改设计文件；越界/符号链接无法计算 revision。
- 限制：文件摘要不提供远程不可删除审计；签名信任仍由 adapter 配置提供；draft 不构成审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，104 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/design-fingerprint-declaration.json`。
