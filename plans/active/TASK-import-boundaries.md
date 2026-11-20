# Python 包导入边界检查

- 类型：Feature；风险：high；涉及 MOD-001、MOD-002、MOD-003、MOD-006、MOD-007。
- AST 导入事实现在按 `src/epe/<module>` 识别 owner，使用默认允许依赖表和版本化 `allowed_imports` 兼容例外，输出违规路径/行号。架构检查将其与图循环和禁止依赖合并。
- 当前仓库的历史兼容导入已显式登记在 architecture policy；这不是永久架构批准，后续重构可逐步消除。
