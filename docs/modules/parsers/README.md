---
id: MOD-002
type: Module
name: EPE Parsers
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# parsers：文档与代码事实提取

## 1. 定位与范围

将 Markdown、YAML 和 Python 代码转换成可追溯的实体候选、符号记录、导入事实和诊断。对应 PRD-002、PRD-003，支撑 AC-02、AC-03、AC-04。

MVP 只承诺结构与静态事实，不评估设计合理性、不批准设计、不自动补全文档，也不以静态分析声称覆盖运行时全部依赖。Tree-sitter 与多语言扩展后续按需求引入。

## 2. 逻辑组件

| 组件 | 职责 | 主要产物 |
| --- | --- | --- |
| Markdown Parser | 识别 YAML Frontmatter，保留正文与字段位置 | DesignCandidate、SourceLocation |
| YAML Parser | 严格读取元数据、契约和策略的结构 | 带位置的字段树与重复键诊断 |
| Python Parser | AST 提取类、函数、签名与导入 | SymbolRecord、ImportFact、AnalysisGap |
| Parse Coordinator | 按输入类型分发，聚合解析统计与诊断 | ParseBatch |

扫描路径由应用和 Repository 端口提供，解析器只接受带路径、字节与摘要的输入。`engineering/` 配置的领域语义由所属模块校验，不能由 YAML Parser 决定权限。

## 3. 对外接口草案

```text
parse_document(source_blob) -> DocumentParseResult
parse_yaml(source_blob, expected_kind) -> StructuredParseResult
parse_python(source_blob, package_roots) -> CodeParseResult
parse_batch(source_blobs, parse_options) -> ParseBatch
```

结果必须包含输入摘要、文件定位、实体候选、符号/导入事实、诊断和覆盖说明。`ParseBatch` 统一记录成功、失败、排除和不支持计数，并在任一错误/不支持时设置 `complete=false`；下游不得将不完整批次发布为完整成功。相同字节与选项生成相同规范化内容，不在解析期间分配随机工程 ID。

普通说明文档可以没有 Frontmatter，返回“非实体文档”；纳管实体路径若被策略要求必须有元数据，则缺失由设计校验报告，不让解析器将正文猜成权威元数据。

## 4. 文档解析规则

Frontmatter 仅在文件开头的明确分隔区域读取。无法闭合、编码错误、重复 YAML 键和不安全 YAML 标签必须诊断，不执行对象构造或模板代码。

无法作为映射键使用的 YAML 值也必须转换为带文件和行号的解析诊断，不能使整次扫描抛出未处理异常。注册阶段对类型错误的枚举、数组和关系来源返回诊断；显式的空对象、布尔值或 null 不得替代数组默认值。

保留正文原始内容与位置，方便后续设计指纹和语义检查。关系与映射仅提取明确声明的字段，正文中出现 `CLASS-001` 不自动建立确定关系；推断提取若未来启用，必须标为 inferred。

字段的类型、必填项和引用由 core Schema 与注册阶段判断；解析器负责忠实读取，避免多处维护相互冲突的字段规则。

## 5. Python 提取与盲区

提取完整限定名、嵌套层级、同步/异步、参数种类、默认值和注解表达式；只解析不 import 目标模块，避免触发业务副作用。类装饰器、条件定义、重载等保留结构信息，不直接推断最终运行类型。

处理 `import`、`from ... import ...`、相对导入与配置的包根。无法唯一解析的外部模块、`importlib`、`__import__`、星号导出和动态注入记录 unresolved / AnalysisGap，交由图模块表达不确定性。

同文件存在多个类和同名嵌套函数时用完整限定名定位。部分语法版本不受当前运行器支持时报告分析不支持；不跳过文件后返回“全量成功”。

## 6. 依赖、缓存与故障

只允许依赖 core；不导入 graph、design、verification 或 adapters 实现。解析不写权威工件，缓存由应用选择持久化。

缓存键至少包含字节摘要、解析器版本、Python 语法版本和解析选项；批次结果按相对路径排序并绑定输入清单摘要。路径改动需更新来源定位与模块名，即使内容字节相同也不能复用错误限定名。

单文件失败保留其他文件诊断用于展示，但批次必须标记 incomplete。索引发布方不能将 incomplete 当完整成功。已排除文件和未支持文件分别统计，避免把未分析当无问题。

## 7. 验证设计

- Frontmatter 缺闭合、重复键、错误编码与未知 YAML 标签，均有文件/行位置。
- 含多个类、嵌套类、异步函数、位置/关键字参数的样例得到可区分符号。
- 相对导入与包根改变后解析事实随配置变化；动态 import 显式报告盲区。
- 文件顶层含危险副作用，AST 分析不执行目标代码。
- 语法错误使批次 incomplete，不能静默发布完整图。
- 修改内容/解析选项/路径后缓存失效；仅改变遍历顺序输出不变。

拟议测试位置为 `tests/unit/parsers/`、`tests/fixtures/parser_cases/`，包含真实 Python 小样例和文档反例。

## 8. 工作包与交付条件

WP-03 交付 Markdown/YAML 解析；WP-04 交付 Python AST 及符号/导入索引。先冻结 ParseBatch 与 SourceLocation，再实现下游图和映射消费者。

交付条件为 AC-02 的解析部分、AC-03/04 的事实提取部分通过，包含不支持范围说明与可重复样例；映射和架构规则是否通过仍由消费者判断。

上游：core 模型与 Repository 读取端口。下游：注册、graph、design、verification。返回[模块索引](../README.md)。
