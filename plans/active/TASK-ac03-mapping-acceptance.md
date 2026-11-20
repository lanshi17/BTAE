# TASK-ac03-mapping-acceptance：实现映射端到端验收

- 分类：Feature；风险：低；影响 MOD-003 Parser、MOD-006 Mapping、MOD-008 CLI；写入范围为验收测试、计划与证据。
- 依据：SPEC AC-03 要求多文件映射正例和已实现类符号删除后阻断。现有测试经进程内 `main` 覆盖删除路径，缺少多文件映射正例和独立 CLI 子进程证明。
- 设计：临时工程声明一个实现实体映射到两个源文件的不同限定符号；真实 `python -m epe mapping validate` 首先通过，随后移除其中一个已映射类并重跑，必须得到非零退出码和 `EPE-MAPPING-SYMBOL`，JSON stdout 单对象且无 traceback。测试不 mock parser、文件系统或 CLI。
- 验收：正例中 checked/symbol 计数和路径真实；删除任一符号后阻断且指出实体与文件。只证明 AC-03 映射场景，不扩大为整个 WP-10 完成声明。

- 结果：真实 CLI 多文件映射正例通过；删除第二个映射类后命令以退出码 1 和定位诊断阻断。定向 1 项、全量 177 项通过；证据见 `reports/evaluations/ac03-mapping-acceptance.json`。
