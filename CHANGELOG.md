# Changelog

## 0.2.3

### Added
- Add a complete bilingual top-level CLI tree and the independent `chatup chrome` contract.
- Add cross-platform Chrome for Testing installation under `~/.chatarch/chrome`, safe archive extraction, atomic metadata, JSON output, and an importable Python descriptor API.
- Add `chatup mysql` to install and prepare a ChatData-compatible user-level MySQL runtime, instance layout, `my.cnf`, user-level systemd service, and optional start/smoke flow.
- Add `chatup nginx` to prepare a user-level NGINX runtime under `~/.chatarch/nginx` and generate common reverse-proxy, HTTPS proxy, WebSocket proxy, static root, and redirect templates.
- Expand `chatup gitea` from binary install into a ChatTea-compatible Gitea runtime/config/service setup flow under `~/.chatarch/chattea`.
- Add a ChatTea-style CLI capability map page and scenario-oriented README/docs index entries for ChatUp.
- Add Material grid-card column layouts to the home, quickstart, and command-reference pages so the docs behave as non-linear task hubs.
- Add ChatArch-standard MkDocs documentation with Chinese/English pages, docs metadata, CI docs build, preview docs workflow, and deploy docs workflow.
- Add `chatup crs` to install the canonical `@chatarch/claude-relay-service` npm package, prepare local Redis, write local configuration and secrets, build the admin SPA, start the service, and run a smoke check.

### Changed
- Replace the legacy system-Chrome/Chromedriver flow with a ChatArch-internal, versioned Chrome for Testing installation while keeping `chatup chrome` as the flat command.
- Align `chatup gitea` with ChatTea defaults: resolve the latest ChatArch Gitea release by default, install under the ChatTea runtime directory, and optionally generate local `app.ini` plus a user-level systemd service.

## 0.2.1

### Added
- Add `chatup uv` to install `uv` when missing and create the ChatArch Python virtual environment with Python 3.12 and pip at `~/.chatarch/venv` by default.

## 0.2.0

### Added
- Migrate ChatTool setup commands into ChatUp as top-level commands, including workspace setup helpers and package assets.
- Add workspace fallback behavior so ChatBlog without `source/_posts` can temporarily link documentation through `public` instead of failing setup.

### Changed
- Require the published shared config runtime `chatenv>=0.2.0,<0.3.0` and bounded ChatArch CLI runtime `chatstyle>=0.1.0,<0.2.0`.
- Use ChatEnv `0.2.x` shared OpenAI/Feishu configs directly from setup modules; ChatUp no longer ships a `chatup.config` package, copied schema definitions, or another `chatenv.configs` provider.
- Remove `chatup alias`; shell alias management stays out of ChatUp's first real setup release.
- Keep `chatup workspace --with-chattool` as repo clone/update only; it no longer copies ChatTool legacy skills such as old TRAE/ToolCall skills into workspace `skills/`. Shared skills should come from linked ChatMemory groups.
- Install ChatArch CC Connect via `@chatarch/cc-connect` while keeping the `cc-connect` binary name.
- Remove the legacy hand-written OpenCode ChatLoop plugin/assets from ChatUp; `chatup opencode --plugin` now keeps only supported presets such as `auto-loop`, because RuffleLoop covers the loop use case.

## 0.1.0

### Added
- Add the initial `chatup` CLI entrypoint with `--help`, `--version`, and `doctor` smoke command.
- Add tag-driven PyPI publish workflow using Trusted Publishing/OIDC.
- Document the ChatUp setup-split role and release requirements.

## 0.0.1

### Added
- Initial placeholder package release for the `chatup` name.
