---
name: btae-coding-agent
description: "Use when designing or changing a software project so the coding agent follows BTAE design-first, traceability, governance, and evidence rules."
---

# BTAE Coding Agent

Use this skill for feature, bugfix, refactor, and exploration work in a BTAE-managed repository. It is the coding-agent entrypoint for the `btae` MCP server; the server provides read-only context, design planning, and validation tools. It does not grant approval, write isolation, or host trust.

## Before editing

1. Read the repository `AGENTS.md` and identify the repository root.
2. Classify the request as Feature, Bugfix, Refactor, or Exploration.
3. Call `btae_project_context` with the objective, change type, and known target entities. Use its sources as C0–C2 context; do not load the whole repository by default.
4. Call `btae_design_plan` before implementation. Treat its result as a draft plan, not as approval. Record the task, affected entities, write scope, protected paths, dependencies, acceptance conditions, and risks in the repository's planning locations.

## Design and implementation rules

- Design first: update the applicable intent/spec, architecture/module boundary, component/class design, contract, ADR, or task plan before changing implementation. Keep the smallest logical entity set; do not create one document per code file mechanically.
- Use stable English entity IDs and preserve identity when files move. Keep Markdown as design intent, machine schemas as constraints, code as implementation, tests as behavior evidence, and execution records as proof.
- Trace both directions: design → implementation/tests and implementation → design. Mark static discovery and model inference as unverified until checked.
- Keep `draft/reviewed/approved`, implementation state, verification result, and evidence validity separate. Never write `approved`, `passed`, or `valid` merely because the agent believes it is true.
- Follow the repository's Feature/Bugfix/Refactor/Exploration workflow. For bugfixes reproduce first; for refactors capture a baseline; for exploration label prototypes and hypotheses.
- Do not change protected paths or execute external commands outside the user's authorized scope. A ChangeSet declaration is not a lock or permission grant.

## Before reporting completion

1. Run the relevant repository checks and preserve real commands, results, timestamps, environment, input/code/contract fingerprints, and artifact paths.
2. Call `btae_validate_project` for the current root. Resolve errors and unknowns or report them explicitly.
3. Check mapping, architecture, scope, evidence freshness, and required checks. A green unit-test count does not prove design conformity.
4. Report changed entities/files, validation commands and results, evidence locations, unresolved risks, and any external approval or host capability still missing.

For the tool contract and client configuration, read [MCP integration reference](references/mcp-integration.md). For the project authority and layer boundaries, use the repository `AGENTS.md`, `docs/intent/requirements/SPEC-BTAE.md`, and `docs/architecture/engineering-protocol.md`.
