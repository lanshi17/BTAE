---
name: btae-coding-agent
description: "Use when designing or changing a software project so the coding agent follows BTAE design-first, traceability, governance, and evidence rules."
---

# BTAE Coding Agent

Applies BTAE discipline to feature, bugfix, refactor, exploration, and worktree-adoption work. It runs in two modes: with the `btae` MCP server, and repo-native without it. It assumes no particular repository layout, language, or toolchain.

## 0. Select the operating mode (first action)

Protocol version: v2. Every task record declares `Protocol: v2`; upgrades follow §8.

Check the host's advertised tool list first. If `btae_project_context` is not listed, do not call it — record `repo-native` directly. If it is listed, call it exactly once with a short objective:

- `mcp`: the call succeeds and returns bounded sources → use it.
- `repo-native`: the tool is not listed, the server is not configured, the call errors, or the result is `status: incomplete` with no sources (the normal case for a repository that is not BTAE's own) → use the fallback table below and say so. Never fabricate tool output or silently skip the step.

Record `Tooling: mcp | repo-native (client=<agent runtime> <version>, date=<YYYY-MM-DD>)`. `client` is the agent runtime name and version (for example `Codex CLI 0.42.0` or `omp 1.4`), not the model vendor alone.

`git check-ignore -v <path>` exits 0 and prints a rule for an ignored path; it exits 1 for a tracked or unignored path. Exit 1 is the normal result for a file that can be committed.

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
- `templates/ADR.md` — decision record for T3 changes and architecture exceptions.

## 2. Classify and size the change

Workflows: Feature (Intent → Spec → Impact/Design → Contract → Implement → Verify), Bugfix (Reproduce → Affected entity → Root cause → Fix design → Implement → Regression), Refactor (Baseline → Snapshot → Impact → Design → Refactor → Regression/Architecture diff), Exploration (Question → Hypothesis → Prototype → Experiment → Evaluation → Decision). Exploration output is a prototype; never present it as production design.

Record `Type: feature | bugfix | refactor | exploration | adoption | governance | tooling`. `adoption`, `governance`, and `tooling` classify the work; a repository with an EPE task schema uses its registered workflow types (`feature`, `bugfix`, `refactor`, `exploration`) and records the governance/tooling scope in the objective and write scope.

Fifth case — Adoption: an uncommitted, half-finished worktree, possibly from another session. See §5.

Change tiers; T2 is the default:

| Tier | Trigger | Required artifacts | Verification |
| --- | --- | --- | --- |
| T1 | one low-risk file, or docs-only with no executable surface; no contract, API, schema, security, or authority change | task record header + objective + 1 acceptance condition + 1 check, ≤ 25 lines | reproduction or focused test; one native check; docs-only link/path check when docs changed |
| T2 | default; multi-file module work, docs that change authority or contract content (`AGENTS.md`, `SPEC`, `ADR`, protocol, schemas), or new/changed governance tooling or checker | intent/spec delta, affected entities, trace table, acceptance | native checks for every touched stack; a negative control when adding a checker or gate |
| T3 | public contract, schema, DB, security boundary, cross-layer or multi-module architecture | ADR / design approval record, scope and dependency analysis | T2 checks + contract tests on both sides + fingerprints |

A docs-only change is T1 only when it cannot alter executable behavior, contracts, schemas, or authority. Editing `AGENTS.md`, `SPEC`, an ADR, the protocol itself, or a machine contract is T2 even when no code changes; adding governance tooling is T2 and must include a check that fails on a deliberately bad input. Never downgrade a tier to avoid documentation; never apply T3 ceremony to a T1 fix.

## 3. Context and design

- Assemble bounded context: target entities/files, direct dependencies, contracts, tests, recent history. Do not load the whole repository by default.
- Design before implementation for T2/T3: update the applicable intent/spec, boundary, component/class design, contract, ADR, or task plan first. Keep the smallest logical entity set.
- Stable English IDs (`REQ-`, `SPEC-`, `ARCH-`, `MOD-`, `COMP-`, `CLASS-`, `CONTRACT-`, `TASK-`, `CHANGE-`, `EVIDENCE-`, `ADR-`). Moving a file must not change identity.
- Trace both directions: design → implementation/tests and implementation → design. Static discovery and model inference stay unverified until checked.
- Keep four states separate: design `draft/reviewed/approved`, implementation `not_started/in_progress/implemented`, verification `pending/passed/failed`, evidence `valid/stale/invalid/unknown`. Never write `approved` or an approval on the user's behalf; only a recorded human or CI approval may do that.
- Declare target entities, write scope, protected paths, dependencies, and risks. With EPE installed, declaration is a `CHANGE-` record checked by `epe changeset`; elsewhere it is the task record's `ChangeSet:` field set to `n/a`. In both cases a declaration is not a lock or a permission grant.

## 4. Implementation

- Change only the declared scope. Unexpected repository changes belong to the user: adapt, do not revert them.
- Keep docs, contracts, code, and tests coherent in one change; delete obsolete aliases and shims instead of layering new ones.
- Commit an evidence record in the same commit as the task record it supports. Commit artifacts only when they are durable, non-secret files the repository already tracks; otherwise keep them at a persistent repository path covered by `.gitignore` and mark temporary ones `ephemeral: true`.
- No secrets, no destructive commands, no external side effects beyond authorization; ask before deleting code you did not write.

## 5. Adoption of an uncommitted worktree

1. Inventory: `git status --short`, `git diff --stat`, untracked list; note files you did not write.
2. Attribute: determine which changes are in scope for this session; never claim authorship of unknown work.
3. Baseline: record the base commit or worktree fingerprint, then run the existing repository checks before editing so pre-existing failures are distinguishable.
4. Fill gaps: add design/spec entries only for what you change; do not retro-document untouched files.
5. Verify the combined result, not only your own delta.
6. Commit only declared-scope files; a whole-worktree commit requires explicit user confirmation. Use selective staging (per-file or staged patches), never `git add -A`.

## 6. Verification and evidence

1. Run the repository checks for touched stacks. Record the exact command, cwd, UTC start/end, exit code, expected exit code, environment, result, and summary. `result` compares `exit_code` to `expected_exit_code`; it does not mean "the process ran". `expected_exit_code` is `0` except for a declared negative control.
2. Fingerprint inputs (source + contract) using the canonical manifest format in [evidence fields](references/evidence.md); list artifacts with path and sha256. A digest is reproducible only when its byte format is fixed — do not invent a different serialization. Exclude the evidence record and the task record that contains it from their own manifest; `validity` is anchored to the remaining inputs.
3. Keep artifacts durable: a repository-relative path or a stable URL. `/tmp` and other session-local files must carry `ephemeral: true` and cannot be the only artifact supporting a gate.
4. For docs-only changes, run the shipped [link/path checker](scripts/check-docs-links.py) and record its exit code. With no positional paths it checks every git-tracked `*.md`; untracked Markdown must be passed explicitly. Use Markdown relative links for cross-document references; backticked paths are for code or commands.
5. With EPE installed, run `epe check [--task TASK-ID]` and `epe verify TASK-ID`; resolve errors and unknowns or report them explicitly.
6. Distinguish "planned check", "ran locally", and "CI-enforced". A green unit-test count does not prove design conformity. If CI configuration or another protected path cannot be changed, do not edit it: include a patch proposal (diff or replacement file) in the report, mark the check `local-only`, and record the missing enforcement as a risk.
7. Mark evidence `stale` when fingerprinted inputs changed after the run. Keep the historical result; never rewrite it to `valid`.

## 7. Report

Report the mode (`Tooling`) with client and version, protocol version, tier, changed entities/files, commands and results, evidence locations, unresolved risks, and any approval or host capability still missing. Mark a check `local-only` when it ran only in the session, especially when protected CI could not be updated; include the proposed CI patch instead of claiming enforcement. Label inference as `[INFERENCE]`; never present it as observed fact.

## 8. Protocol upgrades

- `Protocol: v2` records the rules in force when the record was written. New records use the current version; old records keep theirs.
- Upgrade the protocol as a separate docs task: change the skill, templates, and checker first, then start new records under the new version.
- Never rewrite an old record's historical result to satisfy a new schema. Re-run the check to produce current evidence, and keep the old record as history.
- A version upgrade changes evidence vocabulary only through the documented field set; in EPE-validated records, unknown fields are an error, not an implicit extension.

References: [MCP integration](references/mcp-integration.md) · [verification matrix](references/verification.md) · [evidence fields and freshness](references/evidence.md) · [templates](templates/) · [ADR template](templates/ADR.md)
