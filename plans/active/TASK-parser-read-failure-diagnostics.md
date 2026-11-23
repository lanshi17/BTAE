# TASK-parser-read-failure-diagnostics：递归解析读取故障

- 类型：Bugfix；风险：中；影响 MOD-002 Parsers、MOD-008 CLI。
- 问题：文档与 Python 递归解析器在文件读取期间遇到 `OSError` 时直接冒泡，可能让 CLI 输出 traceback，而不是结构化解析诊断。
- 设计：读取单个文件时捕获 `OSError`，分别返回带规范相对路径的 `EPE-DOC-READ` 或 `EPE-AST-READ`；其余文件继续解析，批次由上层依据 error 诊断保持 incomplete。符号链接和语法/编码诊断语义不变。
- 限制：读取前后的外部写入竞态仍由 manifest/构图新鲜度检查发现；本任务不提供文件系统锁或权限隔离。

## 本轮结果

- 新增文档树和 Python 树读取失败的结构化诊断与单元回归；全量测试和 CLI/架构回归按 PR 证据记录。
