# TASK-repository-git-facts：Repository 与 Git 来源端口

- 类型：Feature；中风险；MOD-009 adapters/core ports、测试和适配器文档；保留既有成果。
- 依据：adapters §2/§5、WP-02 T5。`RepositoryPort.read_bytes` 只有协议没有实现，Git provenance 只返回 dirty 布尔值，无法审查未跟踪和重命名来源。
- 设计：Repository 提供限根 `read_bytes`、`exists` 和规范化相对路径；最终符号链接、越界解析和非普通文件拒绝，读取前后二次确认路径仍在根内。Git adapter 返回 commit、dirty、git_available、porcelain 状态行、未跟踪路径和 rename 状态；命令失败与“无提交”区分，保留兼容字段。
- 验收：真实临时仓库无 Git/有 Git 无提交/脏工作树/未跟踪/重命名分别可观察；路径越界和符号链接拒绝；读取不存在文件返回明确异常。
- 限制：外部写者可在两次路径检查间修改文件；Git 输出仅是来源事实，不授予权限；平台差异需继续评估。状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，110 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/repository-git-facts.json`。
