# TASK-project-positioning-docs：项目定位与用途说明

- 类型：Feature；风险：低；影响 `ARCH-001`、`SPEC-001`、`MOD-008`；范围为 README、文档索引和项目定位说明。
- 目标：让首次接触仓库的开发者、维护者和 Coding Agent 理解 BTAE/EPE 的定位、解决的问题、适用场景、已实现能力和未完成边界。
- 设计：README 保留快速入口；新增 `docs/architecture/project-positioning.md` 作为详细说明，分开描述 BTAE 方法、EPE 引擎、Skill/MCP 接入和宿主适配；不把目标能力或研究假设写成已验证事实。
- 验收：README 与文档索引链接可访问；定位说明包含项目用途、使用者、工作流、能力矩阵、非目标和限制；现有代码与测试不变；Markdown 补充后本地回归仍通过。
