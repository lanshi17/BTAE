# TASK-ac11-task-workflow-acceptance：任务类型与激活门禁验收

- 分类：Feature；风险：中；影响 MOD-007 Governance、MOD-008 CLI；写入范围为 AC-11 验收测试、计划和证据。
- 依据：SPEC AC-11 要求四类任务可登记和校验，缺少验收或范围信息不能激活；工作流额外要求 bugfix reproduction、refactor baseline_manifest、exploration hypothesis。
- 设计：四个隔离临时工程通过真实 CLI 子进程登记 feature/bugfix/refactor/exploration；提供各自特有字段后激活成功。再分别创建缺少 acceptance、bugfix reproduction、refactor baseline_manifest、exploration hypothesis 的任务，要求激活非零并输出对应诊断。任务字段和状态写入 JSON，stdout 单对象。
- 验收：四种类型和状态迁移事实可读；缺少信息不被默认填充；不涉及任务完成门禁或远程 CI。

- 结果：真实 CLI 四类任务均登记并激活；缺少 acceptance 在创建阶段阻断，bugfix/refractor/exploration 缺少 reproduction/baseline_manifest/hypothesis 分别阻断且状态保持 planned。定向 1 项、全量 192 项通过；证据见 `reports/evaluations/ac11-task-workflow-acceptance.json`。
