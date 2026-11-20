# TASK-gate-evidence-order：完成门禁证据排序

- 类型：Bugfix；高风险；MOD-007，涉及 verification 提供的有效性事实。范围为完成门禁、直接回归测试和模块设计；保留现有未提交成果。
- 依据：governance §5、SPEC 完成门禁。现有逻辑先丢弃非 valid 记录再选最新，导致较新的失败、unknown 或 invalid 被较早通过记录掩盖；时间按字符串比较也会错误处理不同时区。
- 设计：先按检查身份、命令、版本、任务和 ChangeSet 找到所有匹配记录，再将具有明确时区的时间解析为实际时间选最新；存在无法排序的记录时保守阻断。最新记录必须全部 valid、passed 并满足测试结果协议；相同瞬间存在不通过记录则阻断。不会根据被删除的记录推断历史完整性。
- 验收：新失败/失效不能被旧通过覆盖；后续新通过可恢复；跨时区按时间而非字符串排序；缺失、非法、无时区时间阻断；不同检查和任务不干扰。
- 状态：draft，不构成审批；系统时钟可信性及记录尾部删除仍未解决。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，88 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/gate-evidence-order.json`。
