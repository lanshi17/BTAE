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
