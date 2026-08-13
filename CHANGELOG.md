# Changelog

## 0.2.11

### Added
- Add `chatup twikoo` to install and manage non-Docker Twikoo comment service instances under `~/.chatarch/twikoo`, including versioned release runtimes, per-instance env/data/log/run directories, user-level systemd units, multi-instance isolation, and smoke checks.

## 0.2.10

### Fixed
- Configure MkDocs Material's `pymdownx.emoji` renderer with Material `twemoji` / `to_svg` so Material icon shorthand cannot leak as literal `:material-*:` text in generated or deployed docs.

## 0.2.9

### Added
- Add a top-level `chatup --tree` readback path that renders the registered CLI tree with command purpose comments.

### Changed
- Align the bilingual CLI tree docs with the runtime-registered tree, including `--help`, `--version`, and `--tree`.

## 0.2.8

### Fixed
- Run generated Zulip memcached container startup as root only long enough to read Docker secret files, then launch memcached with `-u memcache`; this keeps host secret files restrictive while avoiding SASL auth bootstrap failures with Docker Compose versions that ignore `secrets.uid/gid/mode`.

## 0.2.7

### Added
- Add `chatup discourse` and `chatup zulip` service setup commands that keep generated configuration/data under `~/.chatarch/...` and read admin credentials from ChatEnv-managed `DISCOURSE_ADMIN_*` / `ZULIP_ADMIN_*` values without printing secrets.
- Register ChatEnv `Discourse` and `Zulip` admin credential schemas, including `ZULIP_ADMIN_MAIL` as a compatibility alias for `ZULIP_ADMIN_EMAIL`.

## 0.2.6

### Fixed
- Leave ChatEnv `CursorAgent` profile `.env` file permissions to ChatEnv's native storage mechanism; `chatup cursor-agent --save-profile` no longer chmods saved ChatEnv profiles. Cursor-owned auth/config files still use restrictive permissions and wrapper output remains token-free.

## 0.2.5

### Added
- Add `chatup cursor-agent` to install/verify Cursor Agent CLI, safely copy Cursor login/config files with restrictive permissions, register a ChatEnv `CursorAgent` profile schema, support `-e/--env` quick configuration from an env file or profile, and optionally write a token-free file-credential wrapper for migrated auth JSON on macOS.

### Changed
- Detect `~/.local/bin/cursor-agent` / `agent` even when non-interactive PATH omits the standard user bin, so SSH/headless setup can finish without shell rc changes.

## 0.2.4

### Added
- Add the independent `chatup playwright install/path/doctor` backend and `chatup.playwright` Python API for exact Playwright packages and their managed Chromium revisions.
- Store Playwright package, browser cache, executable descriptor, and metadata atomically under `~/.chatarch/playwright`.

### Changed
- Ground Playwright support in the verified Zhihu draft task: ChatUp owns only Playwright/package/browser resolution, while ChatPost continues to own profiles, extensions, bridges, accounts, and publication state.
- Keep the existing Chrome for Testing and ChromeDriver backends independent; Playwright is additive and does not introduce a shared Browser base class.

## 0.2.3

### Added
- Add independent `chatup chrome-for-testing` and `chatup chromedriver` backend groups with install, list, show, path, doctor, remove, and garbage-collection commands.
- Add exact `chatup.chrome_for_testing` and `chatup.chromedriver` Python APIs without a shared public Browser base class.
- Add ChromeDriver installation from official Google manifests, including exact CFT matching, build-compatible browser matching with milestone fallback, and backend-specific metadata.

### Changed
- Remove the ambiguous `chatup chrome` command and `chatup.chrome` import surface without a compatibility alias.
- Store CFT and ChromeDriver artifacts under independent `~/.chatarch/chrome-for-testing` and `~/.chatarch/chromedriver` homes.
- Require `chatstyle>=0.1.1,<0.2.0` so backend commands use the canonical CommandSchema automatic-prompt policy.
- Keep `chromium` absent until ChatUp has a verified Chromium provider and revision contract.

## 0.2.2

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
- Align `publish.yml` with the active PyPI Trusted Publisher's blank environment while retaining job-level OIDC permission.
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
