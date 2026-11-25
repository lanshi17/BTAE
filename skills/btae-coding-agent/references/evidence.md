# Evidence fields, canonical digest, and freshness

Protocol: v2. This reference is portable: the field names below work in a task record in any repository. Only inside the BTAE repository do they also map to `engineering/schemas/evidence.schema.json`; a foreign repository has no obligation to create that file.

## Field set

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` for this field set |
| `id`, `run_id` | `EVIDENCE-` / `RUN-` identifiers; stable, never reused |
| `task_id`, `changeset_id` | Linked work item (`null` when absent) |
| `target_entities` | Design entities the run proves something about |
| `checker`, `checker_version` | Tool that produced the result (e.g. `pytest`, `8.4.1`); use `unknown` rather than omitting an unavailable version |
| `command` | Argument vector as executed, not a paraphrase |
| `cwd` | Working directory of the run |
| `started_at`, `finished_at` | UTC ISO-8601 timestamps |
| `exit_code` | Process exit code, or `null` when no process ran |
| `expected_exit_code` | Exit code that constitutes success for this check; `0` unless the check is an intentional negative control |
| `termination_reason` | Optional short reason for `error` / `not_run`, otherwise `null` |
| `result` | `passed` / `failed` / `error` / `not_run` |
| `validity` | `valid` / `stale` / `invalid` / `unknown` — independent of `result` |
| `input_manifest` | `{entries: [{path, sha256}], digest}` for every fingerprinted input |
| `artifacts` | `[{path, sha256, ephemeral}]` output files; `ephemeral` defaults to `false` |
| `environment` | OS, runtime and tool versions, relevant non-secret env vars |
| `provenance` | `{commit, worktree_digest, host, client}` |

`result` describes whether the run met the declared expectation, not whether the process exited zero. For a normal check `expected_exit_code` is `0`. A negative control sets the expected failure explicitly and records `result: passed` only when the observed `exit_code` equals it; `exit_code: 1` with `result: passed` is therefore meaningful only when `expected_exit_code: 1` is present. A missing `exit_code` when a process ran is a schema/record error, not an expected failure.

`client` is the agent runtime name and version (for example `omp 1.4` or `Codex CLI 0.42.0`), never the model vendor alone. `host` is `<os>/<arch>` (for example `linux/x86_64`). `commit` is the 40-character HEAD SHA or `null`; `worktree_digest` fingerprints uncommitted changes and is `null` for a clean tree.

## Canonical input manifest

A digest is exchangeable only when its bytes are fixed. Use exactly this form:

1. The input set is explicit: the source, contract, and configuration files the check depends on. Do not hash the whole repository unless that is the declared input.
2. `path` is repository-root-relative POSIX text, UTF-8, with no leading `./`, no `..`, and `/` separators.
3. `sha256` is the lowercase hex SHA-256 of the file's raw bytes.
4. `entries` is sorted by `path` (UTF-8 byte order). Paths are unique.
5. `digest` is the SHA-256 of the UTF-8 canonical JSON array of entries: object keys sorted, separators `,` and `:`, no trailing newline, `ensure_ascii=false`.

The aggregate digest hashes one canonical JSON array, not `sha256sum` output and not the pretty-printed JSON:

```text
[{"path":"docs/intent/INTENT-001.md","sha256":"9f2c..."},{"path":"src/example.py","sha256":"4a1b..."},{"path":"tests/unit/test_example.py","sha256":"7d3e..."}]
```

Exact bytes: UTF-8, keys sorted (`path` before `sha256`), separators `,` and `:`, no spaces, no trailing newline, non-ASCII characters unescaped. The digest is `sha256` of exactly those bytes. The following per-file lines are a human review aid only; hashing them, or a `sha256sum` listing, gives a different value and is not the manifest digest:

```text
9f2c...  docs/intent/INTENT-001.md
4a1b...  src/example.py
7d3e...  tests/unit/test_example.py
```

The executable definition (standard library only):

```python
import hashlib
import json
from pathlib import Path


def canonical_manifest(root: Path, paths: list[str]) -> dict:
    entries = [
        {"path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
        for path in paths
    ]
    entries.sort(key=lambda entry: entry["path"])
    raw = json.dumps(
        entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {"entries": entries, "digest": hashlib.sha256(raw).hexdigest()}
```

Shell is fine for listing per-file hashes, but not for the aggregate digest because its serialization differs:

```sh
git ls-files -z -- 'src/**' 'docs/**' | sort -z | xargs -0 sha256sum
```

If two tools disagree, compare the canonical JSON bytes first; the most common causes are `ensure_ascii`, separators, entry order, and a trailing newline.

Do not include the evidence record or the task record that contains it in its own `input_manifest`: the record would change whenever the digest is written, so it can never be valid. Fingerprint the implementation and check inputs, not the description of the run. `validity` is anchored to the remaining inputs: recompute those entries only, and never make a record valid by excluding every input except itself.

A docs link/path check still scans the evidence-bearing Markdown file, because broken references are defects in the record. That scan is not a fingerprint of the record: it validates the record's references, while the manifest excludes the record's own bytes. If the only declared input was the record itself, the evidence is `unknown` (nothing independent was fingerprinted), not `valid`.

## Artifacts and persistence

- An artifact path is a repository-relative POSIX path or a stable URL. `sha256` hashes the recorded bytes (for a URL, the bytes fetched at recording time).
- Prefer a durable path: a tracked report, or a repository path that is intentionally gitignored but survives a restart and is available to the next session.
- `/tmp`, a terminal scrollback, or any other session-local file is `ephemeral: true`. Ephemeral artifacts may illustrate a run but cannot be the only artifact supporting a gate; record the durable summary or copy the output into the repository.
- Commit the evidence block in the same commit as the task record. Commit artifacts only when they are durable and the repository already tracks that kind of output; never commit secrets or generated caches.

## Complete minimal example

This object is valid against the field set above and against EPE's evidence schema inside BTAE. A Markdown task record may embed the same object as YAML; field names and nesting do not change.

```json
{
  "schema_version": 1,
  "id": "EVIDENCE-001",
  "run_id": "RUN-001",
  "task_id": "TASK-001",
  "changeset_id": null,
  "target_entities": ["CLASS-001"],
  "checker": "pytest",
  "checker_version": "8.4.1",
  "command": ["pytest", "-q", "tests/unit/test_example.py"],
  "cwd": ".",
  "started_at": "2026-11-25T08:00:00Z",
  "finished_at": "2026-11-25T08:00:04Z",
  "exit_code": 0,
  "expected_exit_code": 0,
  "termination_reason": null,
  "result": "passed",
  "validity": "valid",
  "input_manifest": {
    "entries": [
      {"path": "src/example.py", "sha256": "<64 hex>"}
    ],
    "digest": "<64 hex>"
  },
  "artifacts": [
    {"path": "reports/tests/pytest.xml", "sha256": "<64 hex>", "ephemeral": false}
  ],
  "environment": {"os": "linux", "python": "3.12.4", "pytest": "8.4.1"},
  "provenance": {
    "commit": "<40 hex or null>",
    "worktree_digest": "<64 hex or null>",
    "host": "linux/x86_64",
    "client": "omp 1.4"
  }
}
```

## Negative controls and expected failures

A checker that must prove it rejects a bad input is a negative control. Declare the failure rather than hiding it in prose:

```json
{
  "checker": "check-docs-links.py",
  "command": ["python", "scripts/check-docs-links.py", "fixture/broken-link.md"],
  "exit_code": 1,
  "expected_exit_code": 1,
  "result": "passed",
  "termination_reason": null
}
```

The same exit code with `expected_exit_code: 0` is `failed` with `termination_reason: "nonzero_exit"`. With a non-zero expectation that does not match, the result is `failed` with `termination_reason: "unexpected_exit_code"`. Do not widen `result` to mean "the command ran"; keep it tied to the declared expectation.

## Freshness and invalidation

Recompute the digests of the recorded `input_manifest` paths. Any difference makes the evidence `stale`: the historical `result` stays as recorded, but the evidence no longer satisfies a gate. Re-run to produce new evidence.

A missing artifact or a mismatched artifact hash makes the evidence `invalid` for gate purposes; it does not change the recorded result. Never edit an old record's `validity` to `valid` by assumption, and never treat a green unit-test run as approval or design conformance.
