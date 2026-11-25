# Verification command matrix

Pick commands in this order: repository-declared (AGENTS.md, package scripts, Makefile) → CI workflow → ecosystem default. Run and record every command actually executed; do not list checks you did not run.

| Stack | Detect | Type/static | Tests | Lint/format |
| --- | --- | --- | --- | --- |
| Node / TypeScript | `package.json`, lockfile | `npx tsc --noEmit` when `tsconfig.json` exists | package `test` script; `npx vitest run` / `npx jest --ci` | package `lint` script |
| Python | `pyproject.toml`, `setup.cfg`, `requirements*` | `mypy .` or `pyright` if configured | `pytest -q` | `ruff check .` |
| Java / Maven | `pom.xml` | `mvn -q -DskipTests compile` | `mvn -q test` | `mvn -q verify` when defined |
| Go | `go.mod` | `go vet ./...` | `go test ./...` | `gofmt -l .` |
| Rust | `Cargo.toml` | `cargo check` | `cargo test` | `cargo clippy -- -D warnings` |
| Docs-only | no code touched | link and cross-reference check | — | markdown lint if configured |

Rules:

- Run only stacks the change touches; a multi-language repo does not require running every stack.
- A command that does not exist is reported as "no configured check", not replaced by an invented one.
- Report pre-existing failures separately from failures introduced by the change.
- Test counts are evidence of execution, not of design conformity; mapping and architecture checks remain separate.
