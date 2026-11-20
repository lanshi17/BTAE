# TASK-init-symlink-safety：初始化路径符号链接安全

- 类型：Bugfix；高风险；MOD-009 Repository/CLI init；范围初始化预检、测试和 adapters 文档；保留其他改动。
- 依据：adapters §4、WP-02 T5、CLI init 流程。当前 init 只检查解析后的目标是否越界，仓库内符号链接父目录/目标可能让写入跟随链接。
- 设计：初始化所有目标文件和目录前，按仓库相对路径逐组件检查；任一已有组件为符号链接即返回 `EPE-PATH-SYMLINK`，不进行任何写入。保留越界解析检测和冲突预检；目录创建也使用同一检查。测试覆盖目标链接、父目录链接、派生目录链接和正常幂等。
- 验收：符号链接场景零写入；已有文件冲突行为不变；正常 init 和重复 init 通过。状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，137 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/init-symlink-safety.json`。
