# TASK-001 — <objective>

<!-- T1: keep this header, Objective, one acceptance condition, and one verification row; omit the other sections. Target ≤ 25 lines. -->

Owner: <person or handle>
Protocol: v2
Type: feature | bugfix | refactor | exploration | adoption
Tier: T1 | T2 | T3
Tooling: mcp | repo-native (client=<agent runtime> <version>, date=<YYYY-MM-DD>)
Risk: low | medium | high
Design status: draft | reviewed | approved  (approval by: <person/record> — leave `draft` if none)
Implementation: not_started | in_progress | implemented
Verification: pending | passed | failed
Evidence: valid | stale | invalid | unknown

## Objective

<One or two sentences.>

## Acceptance conditions

- AC-1: <observable condition>

## Scope

- Target entities: `<ID>`, `<ID>`
- ChangeSet: `<CHANGE-ID or n/a>`
- Write scope: `<paths/globs>`
- Protected paths: `<paths>`
- Dependencies: `<contracts/modules>`

## Design notes (design → code)

<What changes in design/spec/contract, and why. T1 may be one line.>

## Trace table (code → design)

| Entity | Implementation | Verification |
| --- | --- | --- |
| `<ID>` | `<file#symbol>` | `<test>` |

## Baseline / reproduction

<Bugfix, refactor, and adoption: command and observed pre-change result, plus the commit or worktree baseline. Feature: `n/a`.>

## Verification

| Check | Command | Result | Evidence |
| --- | --- | --- | --- |
| `<name>` | `<argv>` | `<passed/failed/error>` | `<path or EVIDENCE-ID>` |

## Risks / open questions

- <Risk, impact, mitigation.>
