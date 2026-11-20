# TASK-ac04-architecture-acceptance：架构门禁端到端验收

- 分类：Feature；风险：中；影响 MOD-002 Parser、MOD-003 Graph、MOD-006 Verification、MOD-008 CLI；写入范围为验收测试、计划和证据。
- 依据：SPEC AC-04 要求发现指定禁止导入、模块循环并明确报告动态分析盲区。现有覆盖分别位于函数级 import boundary、模块聚合 CLI 和单元级 unknown；缺少一条真实 CLI 场景验证聚合报告。
- 设计：临时工程显式配置两个模块根，准备互相导入的模块文件、一个 `epe.core -> epe.cli` 禁止导入和动态 `__import__`。真实子进程执行 init、配置、graph build、architecture validate。验收报告必须同时含 `ARCH-CYCLE`、`EPE-ARCH-IMPORT`、`EPE-ARCH-UNKNOWN`，分别定位路径/行，状态 fail/退出非零；图构建本身保留完整快照。
- 验收：场景不 mock parser、graph 或架构规则；输出来自 JSON CLI。只证明 AC-04 指定违规与盲区场景，不声称静态分析覆盖全部运行时依赖。

- 结果：真实 CLI 单次架构校验同时报告跨模块循环、禁止依赖、模块导入边界违规和动态导入盲区，并定位相应路径/行号。定向 1 项、全量 179 项通过；证据见 `reports/evaluations/ac04-architecture-acceptance.json`。
