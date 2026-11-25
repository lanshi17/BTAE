# Evidence fields and freshness

Aligns with `engineering/schemas/evidence.schema.json` where EPE is installed. Elsewhere, use the same fields in the task record or a Markdown evidence block; do not invent a different vocabulary.

| Field | Meaning |
| --- | --- |
| `id`, `run_id` | `EVIDENCE-` / `RUN-` identifiers; stable, never reused |
| `task_id`, `changeset_id` | Linked work item, when one exists |
| `target_entities` | Design entities the run proves something about |
| `checker`, `checker_version` | Tool that produced the result (e.g. `pytest`, `mvn`) |
| `command` | Argument vector as executed, not a paraphrase |
| `cwd` | Working directory of the run |
| `started_at`, `finished_at` | UTC ISO-8601 timestamps |
| `exit_code` | Process exit code when applicable |
| `result` | `passed` / `failed` / `error` / `not_run` |
| `validity` | `valid` / `stale` / `invalid` / `unknown` — independent of `result` |
| `input_manifest` | `{path, sha256}` entries plus aggregate `digest` |
| `artifacts` | Output files (`{path, sha256}`): reports, logs, coverage |
| `environment` | OS, runtime and tool versions, relevant env vars (no secrets) |
| `provenance` | Commit or worktree fingerprint, host, agent/client |

Non-EPE shorthand block:

```text
EVIDENCE-001
task: TASK-001
command: pytest -q
cwd: <repo root>
started_at / finished_at: <UTC ISO-8601>
environment: <os; python 3.x; pytest 8.x>
exit_code: 0
result: passed
summary: 258 passed, 0 failed
fingerprint: sha256 of the changed source and contract files (sorted path+digest, then hashed)
artifacts: reports/tests/pytest.txt
validity: valid
```

Freshness rule: recompute the digests of the recorded input paths. Any change makes the evidence `stale`; it stays `failed`/`passed` as a historical fact but no longer satisfies a gate. Re-run to produce new evidence. Never edit an old record's `validity` to `valid` by assumption, and never treat a green unit-test run as approval or design conformance.
