# TASK-impact-propagation：双向影响传播

- 类型：Bugfix / Feature，风险：高；受影响实体 MOD-003、影响报告及其 CLI 消费者。
- 依据：graph 模块第 6 节、知识模型关系方向与 WP-12；本任务是 draft 设计，不代表批准或 WP-12 完成。
- 范围：影响传播算法、模块设计、回归测试；不修改实体关系 Schema、旧工作及删除节点历史快照接口。
- 传播规则：realizes 双向、depends_on 由被依赖方至消费者、verified_by / evidenced_by / conforms_to / specifies / affects 按正向传播；不为其它关系猜测传播。Source 与同文件 Symbol 双向连接，依据图中实际节点。起点不列入结果。
- 候选性沿完整路径传递：任何 inferred 或未知来源关系使后续结果成为 candidate；同一节点存在确定路径时可以升级。记录遍历方向、起点和路径。缺失起点、静态盲区及未知导入显式标识 incomplete，预算截断单独记录。
- 验收：代码到设计、设计到代码、消费方及验证链、候选路径传播、循环、替代路径及预算边界均有独立手工预期测试。
- 限制：仍需旧快照删除/移动接口、独立真值集和正式评审；动态依赖无法仅靠静态图确定。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，77 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/impact-propagation.json`。
