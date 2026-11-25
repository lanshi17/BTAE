# TASK-skill-evidence-interop — make skill evidence exchangeable and templates complete

Owner: omp session
Protocol: v2
Type: refactor
Tier: T2
Tooling: repo-native (client=omp (version unreported), date=2026-11-25)
Risk: low
Design status: draft
Implementation: implemented
Verification: passed
Evidence: valid

## Objective

Close the v2 review gaps in the `btae-coding-agent` skill: canonical evidence digests, durable artifacts, a reusable docs checker, explicit reference and tier rules, and complete task/AGENTS/ADR templates.

## Acceptance conditions

- AC-1: `skills/btae-coding-agent/references/evidence.md` fixes digest bytes, artifact persistence, one complete example, commit and migration rules, and scopes the EPE schema to the BTAE repository.
- AC-2: `skills/btae-coding-agent/templates/task-record.md`, `skills/btae-coding-agent/templates/AGENTS.md`, and new `skills/btae-coding-agent/templates/ADR.md` carry Owner, Protocol, Tooling, Baseline, ChangeSet, precedence, and ADR fields.
- AC-3: `skills/btae-coding-agent/scripts/check-docs-links.py` returns 0 on the changed docs and detects broken links, anchors, backticked paths, and undeclared IDs in a fixture.
- AC-4: `skills/btae-coding-agent/SKILL.md`, the integration doc, and the authoritative/packaged evidence schemas agree; the full test suite passes.

## Scope

- Target entities: n/a (skill documentation; no registered entity)
- ChangeSet: n/a
- Write scope: `skills/btae-coding-agent/`, `docs/integrations/btae-coding-agent.md`, `engineering/schemas/evidence.schema.json`, `src/epe/data/schemas/evidence.schema.json`
- Protected paths: none
- Dependencies: `engineering/schemas/evidence.schema.json` (authoritative), packaged schema copy

## Design notes (design → code)

The digest follows EPE's existing canonical JSON (`sha256_json`) instead of inventing a second format, so hand-computed and EPE-produced digests agree. `ephemeral` is an optional artifact field in both schema copies; it changes no existing record. The docs checker is standard-library-only so it works in a copied skill directory.

## Trace table (code → design)

| Entity | Implementation | Verification |
| --- | --- | --- |
| Evidence fields | `skills/btae-coding-agent/references/evidence.md` | `EVIDENCE-002` docs checker |
| Task/AGENTS/ADR templates | `skills/btae-coding-agent/templates/task-record.md`, `skills/btae-coding-agent/templates/AGENTS.md`, `skills/btae-coding-agent/templates/ADR.md` | `EVIDENCE-002` docs checker |
| Docs checker | `skills/btae-coding-agent/scripts/check-docs-links.py` | fixture smoke test + `EVIDENCE-002` |
| Schema alignment | `engineering/schemas/evidence.schema.json`, `src/epe/data/schemas/evidence.schema.json` | `EVIDENCE-001` |

## Baseline / reproduction

Base commit `503453c5a653f4e2d313ec35f7374c8e0f3ca89e`. Pre-change `python -m pytest -q` could not import `epe` without `PYTHONPATH=src`; with it, the only change-related failure was the packaged schema copy, fixed in this task.

## Verification

| Check | Command | Result | Evidence |
| --- | --- | --- | --- |
| Full test suite | `PYTHONPATH=src python -m pytest -q` | passed | `EVIDENCE-001` |
| Docs links/paths | `python skills/btae-coding-agent/scripts/check-docs-links.py --root . skills/btae-coding-agent docs/integrations/btae-coding-agent.md` | passed | `EVIDENCE-002` |
| Checker failure modes | fixture with broken link, path, anchor, ID | detected | `EVIDENCE-002` summary |
| Schema JSON | `python -m json.tool` / packaged-schema test | passed | `EVIDENCE-001` |

## Evidence

### EVIDENCE-001 — full test suite

```json
{
  "schema_version": 1,
  "id": "EVIDENCE-001",
  "run_id": "RUN-001",
  "task_id": "TASK-skill-evidence-interop",
  "changeset_id": null,
  "target_entities": [],
  "checker": "pytest",
  "checker_version": "9.1.1",
  "command": ["env", "PYTHONPATH=src", "python", "-m", "pytest", "-q"],
  "cwd": ".",
  "started_at": "2026-11-25T08:39:57Z",
  "finished_at": "2026-11-25T08:40:47Z",
  "exit_code": 0,
  "termination_reason": null,
  "result": "passed",
  "validity": "valid",
  "input_manifest": {
    "entries": [
      {"path": "docs/integrations/btae-coding-agent.md", "sha256": "c67c125db1bda10e1ccb8168eb0648edb6c84f5c435861e71e7ff9871b66a916"},
      {"path": "engineering/schemas/evidence.schema.json", "sha256": "7a45746d8a676d5bd75c7e417f84678c7a19acc605b03e344e4638576a5068ba"},
      {"path": "skills/btae-coding-agent/SKILL.md", "sha256": "8ab52d7e67339264bf01a1c3defd9ebddc74bc06fcfb579259fdc7a528fef9d5"},
      {"path": "skills/btae-coding-agent/references/evidence.md", "sha256": "49a04ca7a73ff0b886d5394929df9bbe1d863f8487aa7d0b2e0d60211b0901e5"},
      {"path": "skills/btae-coding-agent/references/mcp-integration.md", "sha256": "34b3e22968d98447ff766a29d679e729499dc2b90a8f9b2d3f7535cc67883360"},
      {"path": "skills/btae-coding-agent/references/verification.md", "sha256": "100c495e41bc893371f152460a2b2b81397bddecf5869afd53af046b2ecb84cc"},
      {"path": "skills/btae-coding-agent/scripts/check-docs-links.py", "sha256": "39bb55a43a0e983bc05a7a9b0b63e8ed2c88f2e612367c2e048bbef5ceaf9390"},
      {"path": "skills/btae-coding-agent/templates/ADR.md", "sha256": "4a05cf6c42c20197ad96f337016454c230211a1ee02513f55330a0ddb4e8c678"},
      {"path": "skills/btae-coding-agent/templates/AGENTS.md", "sha256": "b5e524c1eb566c5bb6f0169553f8b217d8e2ee5a929b91f675f5fd0e63d1de59"},
      {"path": "skills/btae-coding-agent/templates/task-record.md", "sha256": "7777aff68badea6166d96bf75cd825f1eebec8fb74e33b6fa61a7701ce344502"},
      {"path": "src/epe/data/schemas/evidence.schema.json", "sha256": "7a45746d8a676d5bd75c7e417f84678c7a19acc605b03e344e4638576a5068ba"}
    ],
    "digest": "50f98665d337979b884661ffd9e9027d71b0783367be2680dde9a543cc2b68ee"
  },
  "artifacts": [],
  "environment": {"os": "linux", "python": "3.14.4", "pytest": "9.1.1", "PYTHONPATH": "src"},
  "provenance": {
    "commit": "503453c5a653f4e2d313ec35f7374c8e0f3ca89e",
    "worktree_digest": "50f98665d337979b884661ffd9e9027d71b0783367be2680dde9a543cc2b68ee",
    "host": "linux/x86_64",
    "client": "omp (version unreported)"
  }
}
```

### EVIDENCE-002 — docs checker

```json
{
  "schema_version": 1,
  "id": "EVIDENCE-002",
  "run_id": "RUN-002",
  "task_id": "TASK-skill-evidence-interop",
  "changeset_id": null,
  "target_entities": [],
  "checker": "check-docs-links.py",
  "checker_version": "unknown (script sha256 39bb55a4)",
  "command": ["python", "skills/btae-coding-agent/scripts/check-docs-links.py", "--root", ".", "skills/btae-coding-agent", "docs/integrations/btae-coding-agent.md", "plans/active/TASK-skill-evidence-interop.md"],
  "cwd": ".",
  "started_at": "2026-11-25T08:39:57Z",
  "finished_at": "2026-11-25T08:39:57Z",
  "exit_code": 0,
  "termination_reason": null,
  "result": "passed",
  "validity": "valid",
  "input_manifest": {
    "entries": [
      {"path": "docs/integrations/btae-coding-agent.md", "sha256": "c67c125db1bda10e1ccb8168eb0648edb6c84f5c435861e71e7ff9871b66a916"},
      {"path": "engineering/schemas/evidence.schema.json", "sha256": "7a45746d8a676d5bd75c7e417f84678c7a19acc605b03e344e4638576a5068ba"},
      {"path": "skills/btae-coding-agent/SKILL.md", "sha256": "8ab52d7e67339264bf01a1c3defd9ebddc74bc06fcfb579259fdc7a528fef9d5"},
      {"path": "skills/btae-coding-agent/references/evidence.md", "sha256": "49a04ca7a73ff0b886d5394929df9bbe1d863f8487aa7d0b2e0d60211b0901e5"},
      {"path": "skills/btae-coding-agent/references/mcp-integration.md", "sha256": "34b3e22968d98447ff766a29d679e729499dc2b90a8f9b2d3f7535cc67883360"},
      {"path": "skills/btae-coding-agent/references/verification.md", "sha256": "100c495e41bc893371f152460a2b2b81397bddecf5869afd53af046b2ecb84cc"},
      {"path": "skills/btae-coding-agent/scripts/check-docs-links.py", "sha256": "39bb55a43a0e983bc05a7a9b0b63e8ed2c88f2e612367c2e048bbef5ceaf9390"},
      {"path": "skills/btae-coding-agent/templates/ADR.md", "sha256": "4a05cf6c42c20197ad96f337016454c230211a1ee02513f55330a0ddb4e8c678"},
      {"path": "skills/btae-coding-agent/templates/AGENTS.md", "sha256": "b5e524c1eb566c5bb6f0169553f8b217d8e2ee5a929b91f675f5fd0e63d1de59"},
      {"path": "skills/btae-coding-agent/templates/task-record.md", "sha256": "7777aff68badea6166d96bf75cd825f1eebec8fb74e33b6fa61a7701ce344502"},
      {"path": "src/epe/data/schemas/evidence.schema.json", "sha256": "7a45746d8a676d5bd75c7e417f84678c7a19acc605b03e344e4638576a5068ba"}
    ],
    "digest": "50f98665d337979b884661ffd9e9027d71b0783367be2680dde9a543cc2b68ee"
  },
  "artifacts": [],
  "environment": {"os": "linux", "python": "3.14.4", "checker": "standard library"},
  "provenance": {
    "commit": "503453c5a653f4e2d313ec35f7374c8e0f3ca89e",
    "worktree_digest": "50f98665d337979b884661ffd9e9027d71b0783367be2680dde9a543cc2b68ee",
    "host": "linux/x86_64",
    "client": "omp (version unreported)"
  }
}
```

## Risks / open questions

- The skill is copied into foreign repositories; the checker path depends on the installed skill location. The command in the verification matrix uses `$SKILL` for that reason.
- ID checking is opt-in because template placeholders and foreign repositories may not declare BTAE IDs.
