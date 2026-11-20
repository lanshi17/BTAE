# TASK-context-cache-freshness：上下文缓存输入与截断

- 类型：Bugfix；高风险；范围 MOD-004 缓存、上下文装配、相关测试与模块设计。保护其他未提交改动。
- 依据：context 模块第 3、5、6 节；现有 manifest 漏掉 AGENTS、测试/契约、归档和可配置证据，源片段 4000 字被无提示截断；映射文件可能在纳管根之外。
- 设计：将全局规则、测试/契约、历史目录和证据位置纳入清单；对选中片段保存完整文件摘要，缓存读取时逐项核对；生成前后清单变化或源读取失败时返回 incomplete 且不缓存。校验源路径解析不得逃出仓库。内容截断和预算遗漏显式列出并标记 incomplete；摘要不提供抗恶意篡改认证。
- 验收：规则、测试、契约、归档、外部映射源或配置证据变化后缓存失效；长规则与缺失目标明确 incomplete；仓库外链接不读取。
- 状态：draft，不代表审批。完整授权范围解析、推断来源分类及独立质量评测仍待完成。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，91 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/context-cache-freshness.json`。
