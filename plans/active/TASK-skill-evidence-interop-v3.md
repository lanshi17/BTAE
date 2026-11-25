# TASK-skill-evidence-interop-v3 — close third-round evidence interop gaps

Owner: omp session
Protocol: v2
Type: governance
Tier: T2
Tooling: repo-native (client=omp (version unreported), date=2026-11-25)
Risk: medium
Design status: draft
Implementation: implemented
Verification: passed
Evidence: valid
Evidence refs: EVIDENCE-003, EVIDENCE-004
Supersedes: none
Superseded by: none

## Objective

Make evidence records mutually checkable across agents: declare expected failures, exclude the record from its own fingerprint, fix digest bytes, define docs-checker discovery, and close the remaining tier/template/CI gaps from the third field review.

## Acceptance conditions

- AC-1: `expected_exit_code` is a schema field, is emitted by EPE, and controls `result`; a wrong expectation is `failed` with `unexpected_exit_code`.
- AC-2: The evidence reference states self-exclusion, anchors `validity` to the remaining inputs, and names the exact aggregate-digest bytes.
- AC-3: The docs checker scans all git-tracked Markdown by default; a tracked broken-link fixture is a passing negative control.
- AC-4: Governance/tooling work is T2 with a negative control; task types and templates carry governance/tooling, supersession, and evidence-reference fields; protected CI gets a patch proposal marked `local-only`.

## Scope

- Target entities: n/a (skill protocol and verification tooling; no registered design entity)
- ChangeSet: n/a
- Write scope: `skills/btae-coding-agent/`, `docs/integrations/btae-coding-agent.md`, `engineering/schemas/{evidence,policy}.schema.json`, `src/epe/{cli.py,core/models.py,data/schemas/{evidence,policy}.schema.json,verification/runner.py}`, `tests/integration/test_{evidence_snapshot_integrity,skill_docs_checker}.py`, `reports/acceptance/skill-evidence-interop-v3-*.txt`
- Protected paths: `.github/workflows/**` (not modified)
- Dependencies: `engineering/schemas/evidence.schema.json` (authoritative), packaged schema copies

## Design notes (design → code)

The canonical digest remains EPE's `sha256_json` over the explicit entry array (UTF-8, sorted keys, `,`/`:` separators, no trailing newline, `ensure_ascii=false`). Switching to concatenated `sha256sum` lines would invalidate every stored EPE manifest; the skill now publishes the exact bytes and an executable definition instead. `expected_exit_code` is optional in the schema (old records stay readable) and defaults to `0`; the runner compares it for command and test checks. Self-exclusion is a record rule, not a checker rule: link checks still scan the record, but its bytes never enter its own manifest. The docs checker keeps the standard library and uses `git ls-files` only when no paths are given.

## Trace table (code → design)

| Entity | Implementation | Verification |
| --- | --- | --- |
| Expected outcome | `src/epe/verification/runner.py`, `engineering/schemas/evidence.schema.json`, `engineering/schemas/policy.schema.json` | `tests/integration/test_evidence_snapshot_integrity.py` (`test_expected_exit_code_makes_negative_control_explicit`) |
| Evidence bytes and self-exclusion | `skills/btae-coding-agent/references/evidence.md`, `SKILL.md` §6 | `EVIDENCE-004` |
| Docs discovery and negative control | `skills/btae-coding-agent/scripts/check-docs-links.py`, `skills/btae-coding-agent/references/verification.md` | `tests/integration/test_skill_docs_checker.py` |
| Tier, type, template, CI rules | `skills/btae-coding-agent/SKILL.md` §2/§6/§7, `skills/btae-coding-agent/templates/task-record.md`, `skills/btae-coding-agent/templates/AGENTS.md` | `EVIDENCE-004` |

## Baseline / reproduction

Base commit `19f002bf1eb797e6b31a1fa6c4063687c51d4b2c`. Pre-change evidence vocabulary had no expected-outcome field, so a negative control could only be explained in prose; the checker scanned a recursive glob, so untracked/build Markdown and a hand-picked path list could miss tracked root READMEs. `PYTHONPATH=src python -m pytest -q` passed before the change; it also passes after.

## Verification

| Check | Command | Result | Evidence |
| --- | --- | --- | --- |
| Full test suite | `env PYTHONPATH=src python -m pytest -q` | passed (365 tests) | `EVIDENCE-003` |
| Docs links | `python skills/btae-coding-agent/scripts/check-docs-links.py --root . skills/btae-coding-agent docs/integrations/btae-coding-agent.md plans/active/TASK-skill-evidence-interop-v3.md` | passed, 10 files | `EVIDENCE-004` |
| Checker negative control | tracked fixture with `[broken](missing.md)` | exit 1, expected 1 → passed | `EVIDENCE-004` |
| Failed expectation | `expected_exit_code: 4`, actual 3 | failed, `unexpected_exit_code` | `EVIDENCE-003` |
| Full-repo docs scan | default discovery over 172 tracked Markdown files | pre-existing 34 planned/example path errors; unchanged by this task | noted, not gated |

## Evidence

### EVIDENCE-003 — full test suite

```json
{
  "schema_version": 1,
  "id": "EVIDENCE-003",
  "run_id": "RUN-003",
  "task_id": "TASK-skill-evidence-interop-v3",
  "changeset_id": null,
  "target_entities": [],
  "checker": "pytest",
  "checker_version": "9.1.1",
  "command": ["env", "PYTHONPATH=src", "python", "-m", "pytest", "-q"],
  "cwd": ".",
  "started_at": "2026-11-25T12:39:20Z",
  "finished_at": "2026-11-25T12:40:14Z",
  "exit_code": 0,
  "expected_exit_code": 0,
  "termination_reason": null,
  "result": "passed",
  "validity": "valid",
  "input_manifest": {
    "entries": [
      {"path": "docs/integrations/btae-coding-agent.md", "sha256": "973926a150efb71afc55032dab3ef5fc32c28f174a1a9c754e3cb5d809f17909"},
      {"path": "engineering/schemas/evidence.schema.json", "sha256": "e51dd822619c24368d1ef58bef3405c634884c9b31755d875226ed52d0e36f3b"},
      {"path": "engineering/schemas/policy.schema.json", "sha256": "4500d86daeef02e5bf6616fcecbbf619d97c8030cf154d1b86c9480e4314ff07"},
      {"path": "skills/btae-coding-agent/SKILL.md", "sha256": "51aea22cd09346fed75af141583fa72ce24eb047a446a00a2b727252307d9b13"},
      {"path": "skills/btae-coding-agent/references/evidence.md", "sha256": "7f48820050de13386b1335c4ae3c0fa7a11c8517c2d246fe1051e6fd32a648e6"},
      {"path": "skills/btae-coding-agent/references/verification.md", "sha256": "e8743dd10f168e334f0be9e3d56cfb60ba384645fd2e63617d190664d8f24485"},
      {"path": "skills/btae-coding-agent/scripts/check-docs-links.py", "sha256": "ab9636c9be310388d207e66bf747f0a3bdfbc13a228b3704f7d3d2ee7270df69"},
      {"path": "skills/btae-coding-agent/templates/AGENTS.md", "sha256": "11abe40b45dfbe5fd7cb5118bdcd207475c0585a59d89bc9764a801cd57628ee"},
      {"path": "skills/btae-coding-agent/templates/task-record.md", "sha256": "92c39d2939ee3d3fae6f89b8246199675b00508de93c6107c51a83ea7d6d489b"},
      {"path": "src/epe/cli.py", "sha256": "cb984153f97f426442852060da51f3e00f90233cd3da26db51c225b0566a9dd1"},
      {"path": "src/epe/core/models.py", "sha256": "4ff2a8e23ff272b49d98d6845e6d0c82a1c5013ba9584fbea305de7d9cf84e40"},
      {"path": "src/epe/data/schemas/evidence.schema.json", "sha256": "e51dd822619c24368d1ef58bef3405c634884c9b31755d875226ed52d0e36f3b"},
      {"path": "src/epe/data/schemas/policy.schema.json", "sha256": "4500d86daeef02e5bf6616fcecbbf619d97c8030cf154d1b86c9480e4314ff07"},
      {"path": "src/epe/verification/runner.py", "sha256": "72e86608e3ed3dd7a6aeeacae4f0c37af57b71b6f3d0585b6b374f4a63916fe9"},
      {"path": "tests/integration/test_evidence_snapshot_integrity.py", "sha256": "c912e6a8a6260b22a952cfb9e86ee5bdc207a5404b8bb99112e43abf1f56027c"},
      {"path": "tests/integration/test_skill_docs_checker.py", "sha256": "acadbd36f7a778a469081500ce61d380b84828644a4a47dc296180910634c2e6"}
    ],
    "digest": "70e89d0b4b291b5e9b92454bb427d4f6e09506fa400c5f4db4efd1a4eaa97eec"
  },
  "artifacts": [
    {"path": "reports/acceptance/skill-evidence-interop-v3-tests.txt", "sha256": "c892c3498f337dbfbbc879bb9e19c12d95ed788cdc6836b5813813447e7e8722", "ephemeral": false}
  ],
  "environment": {"os": "linux", "python": "3.14.4", "pytest": "9.1.1", "PYTHONPATH": "src"},
  "provenance": {
    "commit": "19f002bf1eb797e6b31a1fa6c4063687c51d4b2c",
    "worktree_digest": "70e89d0b4b291b5e9b92454bb427d4f6e09506fa400c5f4db4efd1a4eaa97eec",
    "host": "linux/x86_64",
    "client": "omp (version unreported)"
  }
}
```

### EVIDENCE-004 — docs checker and negative control

```json
{
  "schema_version": 1,
  "id": "EVIDENCE-004",
  "run_id": "RUN-004",
  "task_id": "TASK-skill-evidence-interop-v3",
  "changeset_id": null,
  "target_entities": [],
  "checker": "check-docs-links.py",
  "checker_version": "unknown (script sha256 ab9636c9)",
  "command": ["python", "skills/btae-coding-agent/scripts/check-docs-links.py", "--root", ".", "skills/btae-coding-agent", "docs/integrations/btae-coding-agent.md", "plans/active/TASK-skill-evidence-interop-v3.md"],
  "cwd": ".",
  "started_at": "2026-11-25T12:40:19Z",
  "finished_at": "2026-11-25T12:40:19Z",
  "exit_code": 0,
  "expected_exit_code": 0,
  "termination_reason": null,
  "result": "passed",
  "validity": "valid",
  "input_manifest": {
    "entries": [
      {"path": "docs/integrations/btae-coding-agent.md", "sha256": "973926a150efb71afc55032dab3ef5fc32c28f174a1a9c754e3cb5d809f17909"},
      {"path": "engineering/schemas/evidence.schema.json", "sha256": "e51dd822619c24368d1ef58bef3405c634884c9b31755d875226ed52d0e36f3b"},
      {"path": "engineering/schemas/policy.schema.json", "sha256": "4500d86daeef02e5bf6616fcecbbf619d97c8030cf154d1b86c9480e4314ff07"},
      {"path": "skills/btae-coding-agent/SKILL.md", "sha256": "51aea22cd09346fed75af141583fa72ce24eb047a446a00a2b727252307d9b13"},
      {"path": "skills/btae-coding-agent/references/evidence.md", "sha256": "7f48820050de13386b1335c4ae3c0fa7a11c8517c2d246fe1051e6fd32a648e6"},
      {"path": "skills/btae-coding-agent/references/verification.md", "sha256": "e8743dd10f168e334f0be9e3d56cfb60ba384645fd2e63617d190664d8f24485"},
      {"path": "skills/btae-coding-agent/scripts/check-docs-links.py", "sha256": "ab9636c9be310388d207e66bf747f0a3bdfbc13a228b3704f7d3d2ee7270df69"},
      {"path": "skills/btae-coding-agent/templates/AGENTS.md", "sha256": "11abe40b45dfbe5fd7cb5118bdcd207475c0585a59d89bc9764a801cd57628ee"},
      {"path": "skills/btae-coding-agent/templates/task-record.md", "sha256": "92c39d2939ee3d3fae6f89b8246199675b00508de93c6107c51a83ea7d6d489b"},
      {"path": "src/epe/cli.py", "sha256": "cb984153f97f426442852060da51f3e00f90233cd3da26db51c225b0566a9dd1"},
      {"path": "src/epe/core/models.py", "sha256": "4ff2a8e23ff272b49d98d6845e6d0c82a1c5013ba9584fbea305de7d9cf84e40"},
      {"path": "src/epe/data/schemas/evidence.schema.json", "sha256": "e51dd822619c24368d1ef58bef3405c634884c9b31755d875226ed52d0e36f3b"},
      {"path": "src/epe/data/schemas/policy.schema.json", "sha256": "4500d86daeef02e5bf6616fcecbbf619d97c8030cf154d1b86c9480e4314ff07"},
      {"path": "src/epe/verification/runner.py", "sha256": "72e86608e3ed3dd7a6aeeacae4f0c37af57b71b6f3d0585b6b374f4a63916fe9"},
      {"path": "tests/integration/test_evidence_snapshot_integrity.py", "sha256": "c912e6a8a6260b22a952cfb9e86ee5bdc207a5404b8bb99112e43abf1f56027c"},
      {"path": "tests/integration/test_skill_docs_checker.py", "sha256": "acadbd36f7a778a469081500ce61d380b84828644a4a47dc296180910634c2e6"}
    ],
    "digest": "70e89d0b4b291b5e9b92454bb427d4f6e09506fa400c5f4db4efd1a4eaa97eec"
  },
  "artifacts": [
    {"path": "reports/acceptance/skill-evidence-interop-v3-docs.txt", "sha256": "c7e787e3f0dc2372cdc37a375789a4066fc31782b11e14aab07e6e623d574f33", "ephemeral": false}
  ],
  "environment": {"os": "linux", "python": "3.14.4", "checker": "standard library"},
  "provenance": {
    "commit": "19f002bf1eb797e6b31a1fa6c4063687c51d4b2c",
    "worktree_digest": "70e89d0b4b291b5e9b92454bb427d4f6e09506fa400c5f4db4efd1a4eaa97eec",
    "host": "linux/x86_64",
    "client": "omp (version unreported)"
  }
}
```

## Risks / open questions

- The negative-control fixture is created under `tmp_path` and lives in the test, not in tracked Markdown; this keeps default discovery clean.
- The full-repo default scan currently reports 34 planned/example path references that do not exist yet. They pre-date this task and are not gated; wiring CI would require either creating those paths or adding a reviewed exclude list.
- The aggregate digest stays canonical JSON instead of `sha256sum` lines to remain interoperable with existing EPE manifests. Agents that only implement the newline format will disagree until they use the published canonical bytes.
