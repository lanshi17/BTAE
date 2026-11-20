# TASK-graph-publication-integrity：图快照发布一致性

- 类型：Bugfix；风险：高。范围为 graph 发布与读取、直接相关测试及图模块设计；保护其他工作树改动。
- 依据：SPEC-BTAE 和 graph 模块发布一致性及完整快照要求；任务记录不构成审批。
- 原因：指针切换后兼容文件尚未写完时，读者错误拒绝新图；已有同名 generation 未校验；读取未将 generation 内容绑定指针。
- 设计：指针是发布提交点；兼容文件是非权威派生视图，在提交前写入，指针存在时读取只依赖 generation；旧 generation 保持不变。重用已有 generation 前对比完整图和实体载荷，不一致时拒绝发布。读取校验指针格式及其与完整图摘要相等，避免路径穿越。写入错误不得宣称发布成功。
- 验收：注入指针发布前写失败仍读取旧 generation；损坏已有 generation 不能被重新发布；替换另一份自洽图或非法指针必须拒绝；常规发布和过期检查通过。
- 边界：兼容视图不是事务性接口；尚不保证断电后目录项持久性，也不认证恶意篡改者。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，73 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/graph-publication-integrity.json`。
