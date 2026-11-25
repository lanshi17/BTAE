# BTAE MCP integration

The repository ships a dependency-free stdio MCP server at `mcp/btae_server.py` and an installed entrypoint named `btae-mcp`. It exposes only read-oriented planning and validation operations:

| MCP surface | Purpose |
| --- | --- |
| `btae_project_context` | Assemble bounded C0–C2 project context and source provenance. |
| `btae_design_plan` | Produce a draft BTAE workflow, traceability chain, artifacts, and gates. |
| `btae_validate_project` | Run existing read-only EPE policy/registry/architecture checks. |
| `btae://charter` | Repository `AGENTS.md`. |
| `btae://spec` | BTAE technical specification. |
| `btae://architecture/overview` | Overall architecture design. |
| `btae://workflow/{feature,bugfix,refactor,exploration}` | Machine workflow requirements. |

The server must be registered as a stdio MCP server with the repository root supplied through `BTAE_ROOT` or the tool's `root` argument.

`btae_project_context` assembles sources from BTAE's own layout (`AGENTS.md`, `docs/intent/*`, `docs/architecture/*`, `plans/active/*`). In any other repository it returns `status: incomplete` with an empty `sources` list; that is not an error, and the skill then falls back to the repo-native path in `SKILL.md` §0. Provide `root` for the target project so validation inspects the right tree.

`btae_validate_project` shells out to the target project's `epe`. When EPE is not importable or the project is not initialised, it now returns `status: error` with per-check `exit_code` and `stderr`, instead of a misleading `checked`. Either state means the repo-native checks from `references/verification.md` are the actual evidence.

A Codex config entry is:

```toml
[mcp_servers.btae]
type = "stdio"
command = "/usr/bin/python3"
args = ["/absolute/path/to/BTAE/mcp/btae_server.py"]
env = { BTAE_ROOT = "/absolute/path/to/BTAE" }
```

The MCP entry is an aid for context and planning. It does not replace `epe check`, design approval, ChangeSet scope checks, CI, or host authorization. Do not expose secrets or add write tools without a separately designed contract and gate.
