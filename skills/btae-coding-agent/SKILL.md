---
name: btae-coding-agent
description: "Use when designing or changing a software project so the coding agent follows BTAE design-first, traceability, governance, and evidence rules."
---

# BTAE Coding Agent

Applies BTAE discipline to feature, bugfix, refactor, exploration, and worktree-adoption work. It runs in two modes: with the `btae` MCP server, and repo-native without it. It assumes no particular repository layout, language, or toolchain.

## 0. Select the operating mode (first action)

Probe once, then record the result in the task record or plan header:

- Try `btae_project_context` with a short objective.
- `mcp`: the call succeeds and returns bounded sources → use it.
- `repo-native`: the tool is absent, the server is not configured, the call errors, or the result is `status: incomplete` with no sources (the normal case for a repository that is not BTAE's own) → use the fallback table below and say so. Never fabricate tool output or silently skip the step.

Record `Tooling: mcp | repo-native (<client>, <YYYY-MM-DD>)`.

| BTAE surface | Repo-native substitute |
| --- | --- |
| `btae_project_context` | `AGENTS.md` + module docs + `git status` / `git diff --stat`; bounded, never the whole tree |
| `btae_design_plan` | `templates/task-record.md` + existing plan/spec documents |
| `btae_validate_project` | repository-native type/lint/test commands ([verification matrix](references/verification.md)), each recorded |

MCP provides context and draft planning only. It never grants approval, write isolation, host trust, or a governance pass. A successful or green tool result is not `approved` / `passed`.

EPE CLI commands (`epe init`, `epe task`, `epe check`, `epe verify`, `epe changeset`) exist only when the project has installed that CLI. Probe; do not cite them as if present.

## 1. Establish repository authority

1. Find the repository root (`git rev-parse --show-toplevel`) and read the authority documents that exist: `AGENTS.md`, `CLAUDE.md`, contributor docs, CI config. Never create BTAE's own layout (`docs/intent`, `engineering/`) in a foreign repository unless the user asks to bootstrap it.
2. Prefer declared commands and locations: package scripts, Makefile, CI, existing plans. Do not add a second convention.
3. If no authority document exists and the work is non-trivial, ask one compact question (objective, whether to bootstrap, where plans live), then continue repo-native. Default to continuing, not stalling.
4. Before writing authoritative files, check commit-ability: `git check-ignore -v <path>` for each new charter/spec/task file. If ignored, fix the ignore rule or choose a tracked path. A silently ignored authority document is not evidence and may never reach the repository.
5. Reuse an existing plan/spec/task location before creating one. No empty scaffold directories; no one-document-per-code-file layout.

When bootstrap is explicitly requested or clearly absent, copy the minimal set from `templates/`:

- `templates/AGENTS.md` — scope, authoritative commands, boundaries, evidence rule.
- `templates/SPEC.md` — intent/spec with observable acceptance conditions.
- `templates/task-record.md` — task with separated design/implementation/verification/evidence states.

## 2. Classify and size the change

Workflows: Feature (Intent → Spec → Impact/Design → Contract → Implement → Verify), Bugfix (Reproduce → Affected entity → Root cause → Fix design → Implement → Regression), Refactor (Baseline → Snapshot → Impact → Design → Refactor → Regression/Architecture diff), Exploration (Question → Hypothesis → Prototype → Experiment → Evaluation → Decision). Exploration output is a prototype; never present it as production design.

Fifth case — Adoption: an uncommitted, half-finished worktree, possibly from another session. See §5.

Change tiers; T2 is the default:

| Tier | Trigger | Required artifacts | Verification |
| --- | --- | --- | --- |
| T1 | one file; no contract, API, schema, security, or architecture surface | task record ≤ 15 lines | reproduction or focused test; one native check |
| T2 | default; multi-file module work | intent/spec delta, affected entities, trace table, acceptance | native checks for every touched stack |
| T3 | public contract, schema, DB, security boundary, cross-layer or multi-module architecture | ADR / design approval record, scope and dependency analysis | T2 checks + contract tests on both sides + fingerprints |

Never downgrade a tier to avoid documentation; never apply T3 ceremony to a T1 fix.

## 3. Context and design

- Assemble bounded context: target entities/files, direct dependencies, contracts, tests, recent history. Do not load the whole repository by default.
- Design before implementation for T2/T3: update the applicable intent/spec, boundary, component/class design, contract, ADR, or task plan first. Keep the smallest logical entity set.
- Stable English IDs (`REQ-`, `SPEC-`, `ARCH-`, `MOD-`, `COMP-`, `CLASS-`, `CONTRACT-`, `TASK-`, `CHANGE-`, `EVIDENCE-`, `ADR-`). Moving a file must not change identity.
- Trace both directions: design → implementation/tests and implementation → design. Static discovery and model inference stay unverified until checked.
- Keep four states separate: design `draft/reviewed/approved`, implementation `not_started/in_progress/implemented`, verification `pending/passed/failed`, evidence `valid/stale/invalid/unknown`. Never write `approved` or an approval on the user's behalf; only a recorded human or CI approval may do that.
- Declare target entities, write scope, protected paths, dependencies, and risks. With EPE installed, declaration is a `CHANGE-` record checked by `epe changeset`; elsewhere it is a task-record field. In both cases a declaration is not a lock or a permission grant.

## 4. Implementation

- Change only the declared scope. Unexpected repository changes belong to the user: adapt, do not revert them.
- Keep docs, contracts, code, and tests coherent in one change; delete obsolete aliases and shims instead of layering new ones.
- No secrets, no destructive commands, no external side effects beyond authorization; ask before deleting code you did not write.

## 5. Adoption of an uncommitted worktree

1. Inventory: `git status --short`, `git diff --stat`, untracked list; note files you did not write.
2. Attribute: determine which changes are in scope for this session; never claim authorship of unknown work.
3. Baseline: run the existing repository checks before editing so pre-existing failures are distinguishable.
4. Fill gaps: add design/spec entries only for what you change; do not retro-document untouched files.
5. Verify the combined result, not only your own delta.
6. Commit only declared-scope files; a whole-worktree commit requires explicit user confirmation. Use selective staging (per-file or staged patches), never `git add -A`.

## 6. Verification and evidence

1. Run the repository checks for touched stacks. Record the exact command, cwd, UTC start/end, exit code, environment, result, and summary.
2. Fingerprint inputs (source + contract) and list artifacts by path. Field set and freshness rule: [evidence reference](references/evidence.md).
3. With EPE installed, run `epe check [--task TASK-ID]` and `epe verify TASK-ID`; resolve errors and unknowns or report them explicitly.
4. Distinguish "planned check", "ran locally", and "CI-enforced". A green unit-test count does not prove design conformity.
5. Mark evidence `stale` when fingerprinted inputs changed after the run. Keep the historical result; never rewrite it to `valid`.

## 7. Report

Report the mode (`Tooling`), tier, changed entities/files, commands and results, evidence locations, unresolved risks, and any approval or host capability still missing. Label inference as `[INFERENCE]`; never present it as observed fact.

References: [MCP integration](references/mcp-integration.md) · [verification matrix](references/verification.md) · [evidence fields and freshness](references/evidence.md) · [templates](templates/)
