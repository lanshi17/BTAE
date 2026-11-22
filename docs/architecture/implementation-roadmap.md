# 实施路线、CLI 与验收

状态：v0.1 设计草案。本文的版本号表示目标里程碑，不表示当前已完成对应版本。

本页保持版本路线与研究验证范围；逐项实施步骤、依赖及负责人安排见[实施计划](../../plans/backlog/BTAE-implementation-plan.md)，工作包任务分解见[细化计划](../../plans/backlog/work-packages/README.md)，模块细节见[模块设计](../modules/README.md)。

## 1. 分阶段交付

| 版本 | 目标 | 主要交付 |
| --- | --- | --- |
| V0.1 | 工程规范冻结 | 目录、ID、Schema、模板、四类工作流、Agent Protocol、CLI 及验收规格 |
| V0.2 | 自动化一致性 MVP | Parser、Registry、Mapping、依赖图、设计/测试门禁、Evidence、CI |
| V0.3 | 增量知识与上下文 | 图查询、双向影响分析、Context Resolver、增量更新 |
| V1.0 | 完整工程治理 | 多工作流执行、证据治理、架构协调、Hermes 及其他 Agent 适配 |

实施优先级依次为文档先行协议、文档代码追溯、自动验证、知识图谱、多 Agent 治理。MVP 的基础依赖图属于追溯基础，不要求先建设完整智能图平台。

## 2. MVP 八项能力及验收场景

| 能力 | 最小验收场景 |
| --- | --- |
| Entity Registry | 稳定注册实体；重复 ID 和悬空引用产生诊断 |
| Documentation Parser | 解析元数据及来源；错误格式产生可定位诊断 |
| Code Parser | 提取 Python 类、函数、签名和导入；说明动态分析盲区 |
| Mapping Validator | 发现路径/符号缺失；允许一对多映射与文件移动后的修订 |
| Dependency Graph | 从已验证输入重建图；识别模块循环；保留来源 |
| Design Gate | 缺设计、审批版本失配或无权限时阻断所需操作 |
| Test Gate | 实际执行检查；失败、未执行或未知结果不被标为通过 |
| Evidence Manager | 保存真实结果和输入指纹；相关输入变化后标记 stale |

应采用小型样例工程覆盖正例和反例，验证门禁确实能阻断错误。工具故障、配置缺失与检查发现违规需分别报告。验收测试验证外部行为，避免只复述实现逻辑。

## 3. CLI 目标接口

```text
epe init
epe inspect
epe task create
epe task classify
epe context resolve TASK-001
epe impact analyze CLASS-001
epe design create CLASS-001
epe design validate CLASS-001
epe design approve CLASS-001
epe mapping validate
epe graph build
epe architecture validate
epe verify TASK-001
epe sync
epe check
```

当前已实现 `init`、`inspect`、任务登记/分类、ChangeSet 基线、设计生成/校验/批准、契约 Schema 校验、映射校验、图构建、架构校验、`verify`、`sync`、`check`，基础 `context resolve` / `impact analyze`、增量计划/重建、宿主能力矩阵和结构化 `host request` 入口。`design approve` 只接受配置受信公钥验证的签名记录，不允许调用者自授权限；Hermes 仍明确为未集成 unsupported，CLI 入口不会改变这一状态。

查询命令默认只读；生成命令仅更新声明的派生工件；初始化需避免覆盖现有内容。影响权威工件的操作应提供可审查变更。统一输出诊断、实体 ID、来源和证据定位；机器输出与人类输出共享结果模型。退出码、幂等性、并发和失败恢复在实现前定义。

## 4. 规范冻结前的剩余工作

1. 实现实体、关系、Evidence 以及 Task / ChangeSet、Policy / Workflow 的 Schema。
2. 明确必填字段、关系端点、基数、状态迁移和审批撤销规则。
3. 提供各级设计、契约、ADR、任务与证据模板。
4. 冻结指纹计算范围、环境适用规则、有效期和产物保留策略。
5. 定义风险分类、默认门禁、例外处理与 CI 强制执行位置。
6. 完成 CLI 与 Agent adapter 的请求/响应、错误和授权契约。

这些内容当前属于待交付项，不能仅凭本组架构文档宣称完整 Engineering Specification 已完成。

## 5. 方法有效性验证

核心假设：结构化设计知识、可执行契约、双向追溯、增量影响分析和验证门禁的组合，可能降低长期 Agent 开发中的设计漂移与维护成本。

| 组别 | 开发方式 |
| --- | --- |
| A | 自由 Agent 编码 |
| B | 规格、计划与任务驱动 |
| C | 规格驱动加实体映射与追溯 |
| D | 完整 BTAE |

实验覆盖初始开发、需求变更、长期多轮演进；多 Agent 场景作为单独条件控制。固定或记录模型、提示、工具、任务、预算、环境和执行顺序，重复运行并报告不确定性。实验比较应计入设计编写、索引维护、审批与重跑成本。

主要指标为功能正确性、独立缺陷检出、变更影响召回率/精确率、回归缺陷、架构违规、维护时间、Token 与运行成本。影响分析需独立标注真实影响集合，不能以工具自身图作为唯一真值。

消融项包括类级文档、双向追溯、图能力、设计门禁、架构适应度和 Evidence 管理。组件之间可能存在交互作用，不能将一次移除差值直接解释为普适独立贡献。
