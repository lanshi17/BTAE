# BTAE Coding Agent MCP 入口

本仓库提供一个依赖最小的 stdio MCP 入口，让 coding agent 在设计和修改代码前读取 BTAE 章程、规格和架构上下文，并生成草案设计计划。入口不写入权威文件、不授予审批或宿主权限。

## 暴露的能力

| 名称 | 作用 | 副作用 |
| --- | --- | --- |
| `btae_project_context` | 按目标和变更类型装配有限的 C0–C2 来源 | 只读 |
| `btae_design_plan` | 返回任务字段、追溯链、所需工件和门禁草案 | 只读 |
| `btae_validate_project` | 调用已有 `epe policy validate`、`inspect` 和可用的架构校验 | 只读；不重建图 |
| `btae://charter` / `btae://spec` | 提供权威章程和规格资源 | 只读 |
| `btae://architecture/*` / `btae://workflow/*` | 提供架构与工作流机器来源 | 只读 |

## Codex 配置

### 快速安装 Skill

从 GitHub 安装到用户级 agent 目录：

```bash
npx skills add lanshi17/BTAE --skill btae-coding-agent -g -y
```

从当前本地仓库安装：

```bash
npx skills add . --skill btae-coding-agent -g -y
```

`-g` 表示用户级安装；去掉它即可安装到当前项目。`--skill btae-coding-agent` 避免把仓库中的其他 Skill 一并安装，`-y` 用于非交互环境。

将下面的绝对路径替换为本仓库路径后，加入 `~/.codex/config.toml`：

```toml
[mcp_servers.btae]
type = "stdio"
command = "/usr/bin/python3"
args = ["/absolute/path/to/01_btae/mcp/btae_server.py"]
env = { BTAE_ROOT = "/absolute/path/to/01_btae" }
```

本机默认入口已登记为 `/mnt/data/Projects/Systems/01_btae/mcp/btae_server.py`。其他 MCP 客户端使用同样的 command/args/env 结构即可。

## 使用顺序

1. 先调用 `btae_project_context`，提供 objective、change_type 和 target_entities。
2. 再调用 `btae_design_plan`，把结果保存为仓库中的 draft Task/Plan，并补齐实际实体 ID、ChangeSet 范围和验收条件。
3. 设计明确后才修改实现；完成前调用 `btae_validate_project`。
4. 真实测试、Evidence、审批和最终门禁仍由仓库 EPE CLI 与 CI 负责，MCP 结果不能替代它们。

Skill 入口位于 [`skills/btae-coding-agent`](../../skills/btae-coding-agent)，可复制到目标 agent 的 skills 目录或用 `$btae-coding-agent` 显式调用。

## 两种运行模式

Skill 启动时先探测 `btae_project_context` 是否可用，并把结果写进任务记录：

- `mcp`：工具返回有界来源（仅限 BTAE 自身仓库布局）时使用。
- `repo-native`：工具缺失、未配置、调用报错，或返回 `status: incomplete` 且无来源（普通目标仓库的常态）时使用降级路径：`AGENTS.md` + 模块文档 + `git status/diff` 替代上下文，任务记录模板替代设计草案，仓库原生类型/测试/lint 替代 `btae_validate_project`。

MCP 只提供上下文与草案，不构成批准、写入隔离、宿主信任或门禁通过。

## 目标仓库引导

Skill 附带最小模板 `templates/AGENTS.md`、`templates/SPEC.md`、`templates/task-record.md`，仅在用户明确要求或目标仓库确实没有权威文档时使用。新建权威文档前必须用 `git check-ignore -v <path>` 确认可提交；优先复用已有规划位置，不在普通仓库中预建 `docs/intent/`、`engineering/`。

## 变更分级与接管

- T1：单文件、不涉及契约/结构/安全面的小改，任务记录 ≤ 15 行。
- T2（默认）：多文件模块改动，要求规格增量、实体与追溯表、验收条件。
- T3：公共契约、Schema、数据库、安全边界或跨层架构改动，要求 ADR/设计批准记录、双端测试与指纹。

工作区已有未提交改动时走 adoption 流程：盘点 → 归属 → 基线检查 → 补缺 → 合并验证 → 按声明范围选择性提交，整树提交需用户确认。

验证命令矩阵与证据字段分别见 `skills/btae-coding-agent/references/verification.md` 和 `skills/btae-coding-agent/references/evidence.md`；后者与 `engineering/schemas/evidence.schema.json` 对齐。
