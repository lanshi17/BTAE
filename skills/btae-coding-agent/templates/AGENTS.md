# <PROJECT> Agent Charter

Scope: <what this repository is and is not>. This file is the agent entrypoint; detailed design lives in `<paths>`.

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
- Design first for multi-file or contract-affecting changes; one-file low-risk fixes need only a reproduction and a check.
- Record the exact command, cwd, UTC time, exit code, and result. `passed` is a recorded fact, not an opinion.
- Never write `approved`, sign an approval, or mark evidence `valid` on the user's behalf.
- Keep design, implementation, verification, and evidence states separate.

## Conventions

- Entity IDs: `<prefix scheme>`
- Plans live in: `<path>`; reuse before creating.
- Commit scope: only files declared for the task; confirm before committing unknown work.
