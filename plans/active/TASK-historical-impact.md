# TASK-historical-impact：变更前快照影响追溯

- 类型：Feature；风险：高；实体 MOD-003、MOD-008；写入范围为图读取、CLI、对应设计及测试；保留其他已有改动。
- 设计依据：WP-12 T3，graph 模块第 6 节；本记录为 draft，非批准。
- CLI：`impact analyze OLD_ID --previous-generation DIGEST [--new-entity NEW_ID]`。DIGEST 是此前保留的 generation 的完整 SHA-256，不接受路径；可选 NEW_ID 表示调用者提供的移动后实体，系统不猜测身份。
- 同时要求当前图可读且新鲜。历史 generation 验证完整标记及自身摘要与路径标识；结果分别给出 historical 与 current 报告和版本。历史结果明确不是当前事实，不声称给定快照恰为紧邻变更之前，也不自动推断移动或认定图谱完整。缺失实体或损坏快照阻断；不得将历史快照用于当前无影响结论。
- 验收：实际构图后删除、移动并重建；旧消费者可追溯、新旧结果分离；篡改、错误摘要、缺失实体、当前快照过期拒绝；正常当前分析兼容。
- 限制：调用者选择历史 generation；尚无完整变更集自动配对、独立标注准确率评估或删除节点历史证据完整性保证。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，79 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/historical-impact.json`。
