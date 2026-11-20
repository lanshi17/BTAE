# TASK-evidence-artifact-freshness：验证产物新鲜度

- 类型：Bugfix；风险：高；范围 MOD-006 的验证产物采集、相应集成测试及设计；不覆盖其他工作。
- 依据：SPEC Evidence 关联真实执行、WP-08 T4 与 verification §5。当前仅检查产物运行后存在，先前遗留的文件可被当作本次检查的产物。
- 设计：校验产物配置必须为非空相对路径数组；每个必需产物在执行前记录文件状态，执行后要求新建或文件状态改变，并保存执行后摘要。未更新或不可访问时记录 error，不产生 passed。状态包含内容摘要和文件元数据以兼容生成相同字节的重写；它是本地变化证据，不证明由目标子进程产生，也不抵御外部并发修改。
- 验收：真实命令不写入遗留产物时不得 passed；新建和相同内容重写可通过；越界、错误配置及缺失产物失败；保留诊断证据。文档为 draft，不构成审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，83 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/evidence-artifact-freshness.json`。
