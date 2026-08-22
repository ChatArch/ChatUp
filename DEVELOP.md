# Development Guide

## CLI Rules

- Keep the root command explicitly named `chatup`.
- Use ChatStyle `add_tree_option()` for `--tree` and `--tree-brief`; do not add package-local tree renderers.
- Keep `chatstyle>=0.2.0,<0.3.0` and `chatenv>=0.2.11,<0.3.0` bounded in package metadata.
- Missing required args should auto-enter interactive mode when recoverable.
- `-i` forces interactive mode; `-I` disables prompting and must fail fast.
- Prompt defaults must match actual execution defaults.
- Sensitive values must stay masked in prompts and summaries.
- Explicit ChatEnv profiles must not be backfilled from process-environment credentials.
- Prefer lazy imports in CLI wiring and keep implementation imports local when possible.

## Docs and Tests

- Use doc-first CLI testing.
- Put real CLI coverage under `tests/cli-tests/`.
- Put mock/fake CLI coverage under `tests/mock-cli-tests/`.
- Keep `README.md`, `docs/`, and `CHANGELOG.md` in sync with user-facing changes.

## Automation

- Keep automation small and reviewable.
- Prefer commands that can run in CI without interactive prompts.
- Ensure generated defaults are safe for local development.
- Run tests, strict docs, build, Twine checks, and installed `chatup --version` / `--tree` / `--tree-brief` readbacks before release.
