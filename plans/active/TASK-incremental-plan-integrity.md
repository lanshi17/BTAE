# TASK-incremental-plan-integrity：增量计划可信度

- 类型：Bugfix；高风险；范围 graph 计划函数、CLI 相关测试和 graph 设计；保护已有未提交成果。
- 依据：WP-12 T4 和 graph 模块第 6 节。现有计划仅检查布尔标志和调用方提供的版本字符串，未核验摘要、清单、事实覆盖或包根，可能误报无需重建。
- 设计：对两份快照进行与增量构建相同的完整性及解析环境检查；版本参数还必须与快照实际版本一致。缺少、损坏、不兼容或事实不完整时返回 full_rebuild，并记录原因；仅两份可信且配置相同的快照可计算路径并集差异。CLI 必须首先读取新鲜当前图。
- 验收：使用真实构图产物检查新增、删除及修改；验证篡改摘要、丢失事实、伪造调用参数、代码根变化、旧格式均回退；命令端到端覆盖。摘要不认证恶意伪造的缓存，本记录不构成审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，81 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/incremental-plan-integrity.json`。
