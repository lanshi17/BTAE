# Verification command matrix

Pick commands in this order: repository-declared (AGENTS.md, package scripts, Makefile) → CI workflow → ecosystem default. Run and record every command actually executed; do not list checks you did not run.

| Stack | Detect | Type/static | Tests | Lint/format |
| --- | --- | --- | --- | --- |
| Node / TypeScript | `package.json`, lockfile | `npx tsc --noEmit` when `tsconfig.json` exists | package `test` script; `npx vitest run` / `npx jest --ci` | package `lint` script |
| Python | `pyproject.toml`, `setup.cfg`, `requirements*` | `mypy .` or `pyright` if configured | `pytest -q` | `ruff check .` |
| Java / Maven | `pom.xml` | `mvn -q -DskipTests compile` | `mvn -q test` | `mvn -q verify` when defined |
| Go | `go.mod` | `go vet ./...` | `go test ./...` | `gofmt -l .` |
| Rust | `Cargo.toml` | `cargo check` | `cargo test` | `cargo clippy -- -D warnings` |
| Docs-only | no code touched | `python "$SKILL/scripts/check-docs-links.py" --root . <paths>` | — | markdown lint if configured |

Rules:

- Run only stacks the change touches; a multi-language repo does not require running every stack.
- A command that does not exist is reported as "no configured check", not replaced by an invented one.
- Report pre-existing failures separately from failures introduced by the change.
- Test counts are evidence of execution, not of design conformity; mapping and architecture checks remain separate.
- A new checker or gate needs a negative control: run it against a deliberately bad input, record the non-zero `exit_code`, `expected_exit_code: 1`, and `result: passed`. A checker that has never failed is unproven.
- When CI configuration is protected, do not edit it. Put a patch proposal in the report, mark the check `local-only`, and record that enforcement is missing.

## Docs and cross-document references

[`check-docs-links.py`](../scripts/check-docs-links.py) (standard library, no install) checks relative Markdown links, heading anchors, backticked repository paths, and optionally BTAE ID references. Set `SKILL` to the directory containing this reference, then run it from the repository root:

```sh
python "$SKILL/scripts/check-docs-links.py" --root . docs plans README.md
```

Rules:

- File discovery is part of the contract. With no positional paths, the checker scans every git-tracked `*.md` under `--root` (`git ls-files`), which includes root and nested `README.md`; outside a Git worktree it falls back to a recursive glob. Untracked Markdown is not scanned unless you pass it explicitly. Passing a directory scans all Markdown below it. Exclusion defaults cover `.git`, `.engineering`, virtual environments, `node_modules`, `build`, `dist`, and `__pycache__`; add `--exclude` for project-specific caches.
- Refer to another document with a Markdown relative link, for example `[evidence fields](../references/evidence.md)`, not a bare path. Link text may be human-readable; the target resolves relative to the containing file.
- Use backticks for code, commands, and paths that are not navigation. The checker still validates a backticked token that looks like a repository path (it contains `/` and has a file extension, a trailing `/`, or an existing first directory).
- Anchor checks apply to Markdown targets; GitHub-style heading slugs are used, including `-1`, `-2` suffixes for duplicate headings.
- `--check-ids` verifies that `TASK-`, `REQ-`, `SPEC-`, `ARCH-`, `MOD-`, `COMP-`, `CLASS-`, `CONTRACT-`, `CHANGE-`, `EVIDENCE-`, `ADR-`, and `RUN-` IDs referenced in backticks are declared in a heading, a `key: ID` line, or a bare ID line in the scanned files. Enable it only where those declarations exist; template placeholders should be excluded or left out of the scan.
- Exit `0` means no problems, `1` means at least one broken reference, and `2` means a usage error. Record the exact command and exit code as evidence.
