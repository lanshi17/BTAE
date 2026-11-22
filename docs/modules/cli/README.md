---
id: MOD-008
type: Module
name: EPE CLI
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# cli：命令入口与应用装配

## 1. 定位与范围

提供统一人类/机器入口，装配内部服务和端口实现，执行用例并输出稳定结果。对应 PRD-001、PRD-008、PRD-009，主要验收 AC-01、AC-09、AC-11，并承载其余验收的端到端入口。

CLI 管参数、装配和流程，不内嵌审批、证据有效性或架构规则算法。当前提供 SPEC 首批命令、`context resolve`、`impact analyze` 和安全 `design create`；不具备可靠实现的宿主能力仍明确返回 unsupported。

## 2. 逻辑组件

| 组件 | 责任 |
| --- | --- |
| Command Router | 参数校验、根目录解析、命令分发 |
| Composition Root | 将 Repository / Process / Git 等 adapter 注入业务服务 |
| Application Use Cases | 顺序调用解析、校验、授权、执行和发布步骤 |
| Result Presenter | 共用结果模型的 text / JSON 输出 |
| Exit Mapper | 按统一规则转换退出码，保留全部诊断 |

应用编排可以位于本模块的独立子包，不能把所有逻辑放入 main 函数；它只协调用例，不成为新的领域规则权威。

## 3. 命令与副作用

| 命令组 | 主要协作模块 | 允许副作用 |
| --- | --- | --- |
| init | governance、adapters | 创建缺失配置/模板，拒绝覆盖冲突 |
| inspect | core、adapters | 默认只读 |
| task create / classify | core、governance、adapters | create 登记任务；classify 只读 |
| design validate / approve | design、governance、adapters | validate 只读；approve 追加可信记录 |
| mapping validate | parsers、core、verification | 不修改源与设计 |
| graph path | graph、adapters | 只读查询新鲜图，支持方向、关系和预算过滤 |
| graph build / sync | parsers、core、graph、adapters | 更新派生快照，不回写权威设计 |
| changeset transition | governance、adapters | 在 revision 和实际范围校验下迁移 planned/active/completed/aborted |
| architecture validate | graph、verification、governance | 只读检查，报告结果 |
| verify | governance、verification、adapters | 启动已授权检查，追加产物与 Evidence |
| check --task | 全部 MVP 事实提供者、governance | 汇总当前事实，不隐式启动测试 |
| host request | adapters、Agent Protocol | 发送结构化宿主请求；仅报告宿主决定，不授予治理权限 |

签名与必需参数以 SPEC 第 8 节为准。所有命令支持 `--root PATH`、`--format text|json`；不因运行在子目录就扩大纳管范围。

## 4. 对外结果契约

```text
CommandResult = {
  schema_version, command, status,
  diagnostics[], data, evidence_ids[]
}
```

status 为 passed/blocked/error/unsupported。JSON stdout 仅含一个完整结果，不输出进度、子进程日志或 ANSI 色彩；日志与进度走 stderr。Text 与 JSON 来自同一结果对象，不能一种隐藏 warning。

退出码：0 成功，1 门禁阻断，2 参数/配置错误，3 执行/解析/存储故障，4 不支持，5 写入冲突。混合结果优先返回故障而非普通阻断；具体故障类别与多个故障同时出现的优先表在 WP-01 冻结，不能依赖异常捕获顺序。

## 5. 关键用例流程

**初始化**：解析根与已有配置 → 校验可信初始化输入 → 构造写入计划 → 全量冲突预检 → 取得仓库写许可 → 仅创建缺失文件 → 输出变更清单。遇到已有不同内容时不覆盖，说明需要人工合并；中断时仅清理由本次创建且未被外部修改的临时内容。

**历史影响**：`impact analyze OLD_ID --previous-generation DIGEST [--new-entity NEW_ID]` 使用指定的历史 generation；必须存在新鲜当前图，结果分开标记历史与当前，移动后的实体由调用方指定。

**检查**：读取同版本事实 → 验证缓存新鲜度 → 按需进行只读解析/检查 → 收集现有 Evidence → governance 计算决定 → 展示未执行项。没有测试证据时返回缺失，不借 check 偷跑测试。

**验证**：解析 Task 与 ChangeSet → 权限门禁 → 形成 ExecutionPlan → verification 运行并留证 → 重新核对版本 → 输出结果。客户端不能通过参数直接更改运行命令或审批角色。

**宿主请求**：校验请求值对象 → 选择 `local-cli` 或显式 argv 的 Hermes adapter → 完成能力握手 → 输出 `accepted/blocked/unsupported/error`。该命令不修改权威工件；`--identity-source` 不构成认证，写入类操作在未受信宿主上保持 `unsupported`。

## 6. 依赖、幂等性与异常

允许依赖所有内部模块，仅本组合入口选择具体 adapter。其他模块不得反向导入 CLI。共享 DTO、诊断和端口应在 core，不将 argparse/Click/Typer 类型传播到领域服务。

init 重复执行不改已有内容；图重建内容幂等；verify 每次产生独立 Run ID；approve 重复相同不可变记录可返回已存在，冲突记录拒绝。写入锁失败用退出码 5，不无限等待。

顶层捕获可预期故障并输出结构化诊断；取消验证要求终止本次子进程组并保留可用证据。程序内部错误不能转换为 0，默认不暴露含敏感数据的原始调用栈。

## 7. 验证设计

- 对每个 MVP 命令验证参数错误、正常结果和领域阻断。
- 在含已有配置的仓库 init，所有原文件字节不变；冲突前预检不发布部分配置。
- 收集子进程大量 stdout/stderr 后，父 CLI 的 JSON 仍是单一可解析对象。
- check 不执行配置命令；verify 必须留下真实 Run ID 和 Evidence 定位。
- 在未初始化、无提交、子目录、路径含中文/空格环境下运行，根定位与退出码正确。
- 打断快照写入或运行第二写者，输出故障/冲突，不谎报成功。

拟议测试位于 `tests/acceptance/cli/`，通过真实 CLI 子进程和临时仓库验证，不只调用命令函数。

## 8. 工作包与交付条件

WP-02 建立可安装入口与最小 inspect；WP-09 集成全部 MVP 命令；WP-10/11 完成验收与 CI。选择命令框架时以稳定参数与机器输出优先，不把框架选择当产品能力。

交付需具备命令帮助、JSON 契约、完整退出码测试、样例教程、wheel 源码外安装验证和未支持命令说明。运行时依赖必须写入项目元数据；源码树中预装依赖不构成发布验证。CI 通过只表示该工作流执行了检查，未配置远程分支保护时不能称为合并门禁。只有真实运行证据可标注可用命令，不能把文档示例变成实现完成声明。

上游：各服务和 adapters。下游：开发者、CI、后续 Agent adapter。返回[模块索引](../README.md)。
