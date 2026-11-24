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

The server must be registered as a stdio MCP server with the repository root supplied through `BTAE_ROOT` or the tool's `root` argument. A Codex config entry is:

```toml
[mcp_servers.btae]
type = "stdio"
command = "/usr/bin/python3"
args = ["/absolute/path/to/BTAE/mcp/btae_server.py"]
env = { BTAE_ROOT = "/absolute/path/to/BTAE" }
```

The MCP entry is an aid for context and planning. It does not replace `epe check`, design approval, ChangeSet scope checks, CI, or host authorization. Do not expose secrets or add write tools without a separately designed contract and gate.
