# TASK-context-task-scope：任务范围与策略上下文

- 类型：Feature；高风险；MOD-004 与 MOD-008；范围上下文来源装配、CLI 输入校验及测试；保留其他未提交工作。
- 依据：context §4–5、WP-13 T3。现有 CLI 上下文没有任务 ChangeSet 和有效策略来源，不能帮助执行端识别声明范围。
- 设计：CLI 解析任务绑定的 ChangeSet，通过既有校验器检查 ID、关联和结构，将文件和架构/验证策略文件以 C0 来源注入 resolver；缺失/非法关联时列出 omission、返回 incomplete，不缓存。策略文件是待评估来源，ChangeSet 是声明，不表示授权或实际锁。缓存键绑定来源列表和其内容摘要；大文件截断仍标 incomplete。
- 验收：真实 CLI 返回范围和策略；修改关联记录不命中旧缓存；关联缺失、结构错误及 C0 预算不足标 incomplete；源文件不可越界。
- 局限：不对调用者身份和批准做授权裁决，未验证的策略不可描述为有效；draft 不构成设计审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，94 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/context-task-scope.json`。
