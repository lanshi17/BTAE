# WP-04：Python AST、符号与映射检查

**状态：** planned · **里程碑：** M1 · **实施：** not_started  
**负责模块：** parsers、[verification](../../../docs/modules/verification/README.md)  
**前置：** WP-02 · **可并行：** WP-03 · **下游：** WP-05、WP-08

## 1. 目标

从不 import 目标代码的前提下提取类/函数/签名/静态导入；实现 Mapping Validator，使已声明 implemented 的缺失符号可阻断。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 实现 `parse_python` → `CodeParseResult`（SymbolRecord、ImportFact、AnalysisGap） |
| T2 | 完整限定名、嵌套类、async、参数种类与注解表达式 |
| T3 | 相对导入 + 包根配置；歧义/动态 import 记 unresolved |
| T4 | 语法错误 → 文件级故障且批次 incomplete |
| T5 | Mapping Validator：一实体多文件、同文件多实体；draft 未来路径不伪称已实现 |
| T6 | 删除已实现符号的回归夹具 |
| T7 | 确认分析过程无目标模块副作用（含危险顶层语句样例） |

## 3. 拟议路径

```text
src/epe/parsers/python_ast.py
src/epe/verification/mapping.py
tests/unit/parsers/test_python_ast.py
tests/unit/verification/test_mapping.py
tests/fixtures/parser_cases/python_*/
tests/fixtures/mapping_cases/
```

## 4. 映射判定表

| 设计状态 / 实现声明 | 路径或符号缺失 | 结果 |
| --- | --- | --- |
| `implemented` | 是 | **阻断**（mapping fail） |
| `not_started` / draft 未来路径 | 是 | 待办诊断，不冒充实现通过 |
| 多 path/symbol 均存在 | 否 | pass |
| 动态依赖导致无法确认 | — | AnalysisGap；不静默当无依赖 |

## 5. 验收映射

AC-03；AC-04 中“动态盲区显式报告”的事实提取部分。架构违规判定属 WP-05。

## 6. 完成门槛

- [ ] AST 路径不 `import` 被分析模块
- [ ] AC-03 正反夹具通过
- [ ] 不支持语法版本有明确诊断，非“全量成功”
- [ ] Mapping Validator 不依赖 adapters 具体实现（端口或纯数据输入）
