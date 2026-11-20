# WP-03：文档与结构化工件解析

**状态：** planned · **里程碑：** M1 · **实施：** not_started  
**负责模块：** [parsers](../../../docs/modules/parsers/README.md)、core  
**前置：** WP-02 · **可并行：** WP-04（共享 WP-01 的 SourceLocation / ParseBatch 契约）

## 1. 目标

严格解析 Markdown Frontmatter 与 YAML 结构化工件，产出带来源定位的实体候选与诊断；普通说明文档不得被猜成已注册设计。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 冻结并实现 `SourceLocation`、`DocumentParseResult`、`ParseBatch` |
| T2 | Markdown：仅文件头分隔 Frontmatter；缺闭合/编码错误可定位 |
| T3 | YAML：重复键报错；拒绝不安全标签与任意对象构造 |
| T4 | 区分非实体文档 vs 纳管实体缺元数据（后者留给 design 校验） |
| T5 | 关系字段只提取显式声明；正文中的 ID 文本不自动建边 |
| T6 | 批量解析统计：成功/失败/排除/不支持；incomplete 标志 |
| T7 | 正反夹具与单元测试；确认不执行文档内代码 |

## 3. 拟议路径

```text
src/epe/parsers/
  markdown.py
  yaml_strict.py
  coordinator.py
  models.py
tests/unit/parsers/
tests/fixtures/parser_cases/
  docs_valid/
  docs_invalid/
```

## 4. 关键行为

| 输入 | 期望 |
| --- | --- |
| 合法 Frontmatter + 正文 | 候选实体 + 位置 + 输入摘要 |
| 重复 YAML 键 | 错误诊断，含 path/line |
| 无 Frontmatter 的 README | 非实体文档，非错误（除非策略强制） |
| 重复 ID（跨文件） | 解析可产出候选；注册阶段冲突（与 WP-02 衔接用例） |
| 悬空关系 to | 解析保留边候选；注册/构图阶段诊断 |
| incomplete 批次 | 不得被调用方标为完整成功发布 |

## 5. 验收映射

AC-02 的文档解析部分；模块 parsers §7。不声称 AC-03/04（代码侧）。

## 6. 完成门槛

- [ ] 解析器包仅依赖 core
- [ ] 正反夹具覆盖上表
- [ ] incomplete 与非实体文档语义有测试断言
- [ ] 文档明确：解析器不执行目标文档代码、不写权威工件
