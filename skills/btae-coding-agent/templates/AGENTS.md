# <PROJECT> Agent Charter

Scope: <what this repository is and is not>. This file is the agent entrypoint; detailed design lives in `<paths>`.

## Precedence

When sources conflict, apply them in this order and record the conflict instead of silently choosing:

1. An explicit instruction or approval from the repository owner for the current task.
2. This `AGENTS.md` (scope, commands, boundaries).
3. `SPEC`, architecture, and contract documents.
4. Task records and plans.
5. Coding-agent protocol defaults (for example the BTAE skill).

## Repository map

| Area | Path | Notes |
| --- | --- | --- |
| Source | `src/` | |
| Tests | `tests/` | |
| Design | `docs/` | |

## Authoritative commands

| Purpose | Command |
| --- | --- |
| Install | `<cmd>` |
| Type/static | `<cmd>` |
| Test | `<cmd>` |
| Lint | `<cmd>` |

Commands here override ecosystem defaults. If a command is absent, say so instead of inventing one.

## Boundaries

- Protected paths (require explicit approval): `<paths>`
- Forbidden operations: secrets in tree, destructive git commands, production data access, network side effects outside scope.
- Bindings/config: `<files>`

## Workflow and evidence

- Classify work as feature / bugfix / refactor / exploration / adoption.
- Start each task record with `Protocol: v2`, `Tooling: mcp | repo-native (client=<runtime> <version>, date=<YYYY-MM-DD>)`, and the tier.
- Design first for multi-file or contract-affecting changes; one-file low-risk fixes need only a reproduction and a check.
- Record the exact command, cwd, UTC time, exit code, and result. `passed` is a recorded fact, not an opinion.
- Use the canonical input-manifest format for fingerprints; a digest without its byte format is not evidence.
- Keep artifacts at durable repository paths (or stable URLs); mark `/tmp` outputs `ephemeral: true`, and never let an ephemeral file alone support a gate.
- Never write `approved`, sign an approval, or mark evidence `valid` on the user's behalf.
- Keep design, implementation, verification, and evidence states separate.

## Conventions

- Entity IDs: `<prefix scheme>`
- Plans live in: `<path>`; reuse before creating.
- Commit scope: only files declared for the task; confirm before committing unknown work.
