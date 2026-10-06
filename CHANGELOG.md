# Changelog

## Unreleased

### Added
- Add Windows-hosted native Node/Codex/OpenCode setup checks, including managed runtime/npm prefix, current-user PATH readback and an isolated Hermes installer path probe.
- Make Cursor Agent use its official native Windows installer and ChatArch Hermes use the fork's PowerShell installer with explicit home/path readback.
- Add a bounded Windows-native GitHub Actions smoke job for the official Node.js LTS ZIP bootstrap and Codex/OpenCode npm/configuration paths, using isolated HOME, USERPROFILE, CHATARCH_HOME, CODEX_HOME, and OPENCODE_HOME values plus a non-secret placeholder.

### Fixed
- Let `chatup nodejs` persist its managed runtime and npm launcher directories to current-user Windows PATH with readback and idempotent updates.
- Reuse the shared shell-free Node/npm runtime in Remotion and discover Lark CLI's managed Windows launcher after installation.
- Preserve unrelated Claude settings and honor `CLAUDE_CONFIG_DIR`; align FRP Windows architecture names, fail installation errors nonzero and refuse overwriting existing binaries/configurations.
- Guard native installer failures against untrusted diagnostic output, and verify the Hermes requested paths before installation.
- Make `chatup nodejs` bootstrap an official SHA-256-verified portable Node.js LTS ZIP under ChatArch home on Windows when PATH has no suitable runtime. Extraction is bounded and rejects unsafe archive paths; repeated setup reuses the managed runtime.
- Run Windows npm operations through the detected `node.exe` and `npm-cli.js` with argv lists and a runtime-prepended child PATH, including the Playwright installer, instead of executing npm `.cmd` launchers directly. Packages installed globally through a ChatArch-managed runtime use the contained `$CHATARCH_HOME/nodejs/npm` prefix.
- Make `chatup codex` honor `CODEX_HOME` and preserve unrelated native Codex config/auth fields while updating supported root-level `model`, `model_provider`, and `forced_login_method = "api"` settings.

## 0.2.22

### Added
- Add bare `chatup glance` setup for the latest stable maintained `ChatArch/glance` release, with strict tag selection, custom runtime homes and side-effect-free dry runs.
- Verify the exact Linux amd64 archive, `SHA256SUMS`, `BUILDINFO.txt`, source revision and observed binary version, then reuse ChatGlance's portable initialization and safe binary installer.

### Safety
- Preserve existing config/data and only reuse an exact provenance match. Refuse replacement and direct explicit upgrades to `chatglance runtime update`; never start a server, enable a service, create a public endpoint or write credentials.

## 0.2.21

### Added
- Add `chatup snipaste` for verified Snipaste installation on macOS and Windows. Windows uses the exact WinGet `liule.Snipaste` package, accepts agreements only with `--yes`, and verifies package-manager records before reporting success.

### Fixed
- Use the versioned `Google.Chrome.EXE` WinGet package for current-user Windows Chrome installation, avoiding floating MSI hash mismatches without bypassing verification. Verify the installed executable's Google signature, identity and version, and reuse existing user/machine installations.
- Make `chatup workspace` optional module setup friendlier on Windows: detect Git for Windows in common install locations, report a clear error when Git is missing, pass the directory symlink flag, and fall back to junctions/hard links when symlink privileges are unavailable.
- Preserve spaces and shell metacharacters in Windows junction paths, decode Git output as UTF-8, and mark extracted directory symlinks correctly on Windows.
- Refresh workspace documentation examples to use the supported single-argument workspace path form.

## 0.2.20

### Added
- Add Blender to `chatup macos` on Apple Silicon, selected by default with the existing apps. Verify the pinned official Blender 5.2.2 LTS DMG SHA-256, bundle version, publisher signature and notarization; reuse existing verified installs. Intel retains the original three default apps and rejects explicit Blender selection before installation.
- Add `chatup remotion PROJECT_DIR` with a locked Remotion 4.0.530 / React 19.1.0 starter, Node/npm checks, safe staged project creation, existing-directory protection and dependency verification on repeated runs. Install dependencies locally without lifecycle scripts or global runtime changes.
- Detect existing Chrome/Chromium for render guidance, support explicit browser paths, interactive directory selection and read-only previews, and package the reproducible starter and lockfile in wheel/sdist.

## 0.2.19

### Added
- Add `chatup macos` with a ChatStyle checkbox menu for Snipaste, iTerm2 and Google Chrome, all selected by default. Support repeated `--app`, `-i`/`-I`, empty selection and side-effect-free `--dry-run`.
- Install Snipaste on macOS from its official DMG, verifying its bundle identity and Developer ID signature through the existing staged desktop installer. Reuse existing Chrome and iTerm2 installations.
- Include ChatStyle's TUI dependencies so default installations provide the checkbox menu. Non-interactive runs install explicit choices or the three defaults; unsupported systems fail before installation.

### Fixed
- Keep simulated desktop app bundles in a non-indexed directory and clean them after tests, preventing duplicate application entries on macOS development machines.

## 0.2.18

### 修复
- `chatup zsh` 将官方源安装快捷名称由 `pypi` 改为 `pypip`；保留原命令及镜像 URL，`tspip` 不变。

## 0.2.17

### Added
- Add `chatup chrome` to install regular Google Chrome for the detected OS: the official universal DMG on macOS, exact `Google.Chrome` through WinGet on Windows, and the official x86_64 DEB/RPM through apt/dnf/yum/zypper on Linux.
- Add `chatup iterm` to install iTerm2 from its official stable ZIP on macOS; reject other operating systems explicitly.
- macOS installation requires no Homebrew, verifies bundle identity/version and publisher signatures, and uses `/Applications` or user Applications with staged installation. Existing apps are verified and reused without upgrades or profile changes.
- Add side-effect-free `--dry-run`, explicit Linux `--sudo`, package-manager `--yes`, installation logs, and post-install verification. Keep Chrome for Testing, ChromeDriver and Playwright independent.

## 0.2.16

### 修复
- `chatup uv` 默认在已有 `~/.bashrc` 和 `~/.zshrc` 中追加或更新 ChatArch venv 自动激活块；新建、修复和复用环境均生效，不创建缺失的 rc 文件。
- 新增 `--activate / --no-activate`，默认开启；关闭时不修改或移除已有启动配置，Windows 跳过 Bash/Zsh 更新。
- 复用 ChatUV 标记，避免重复激活；保留块外用户内容，以绝对路径和 shell quoting 处理自定义 venv，未变化的 rc 不重复写入。
- rc 文件写完并同步后原子替换，保留原权限和符号链接；写入失败时保留原始配置。

### 变更
- `chatup codex` 和 `chatup hermes` 的默认模型统一为 `gpt-5.6-terra`（GPT-5.6 Terra）；仅修改未配置模型时的兜底值，保留显式参数、profile、已有配置和环境值的优先级。

### 新增
- `chatup chatgpt` 安装新版官方 ChatGPT 桌面应用（含 Codex），与现有 `chatup codex` CLI 配置入口分离。
- macOS 使用 Homebrew `homebrew/cask/chatgpt`，Windows 使用官方 Microsoft Store 精确 ID `9PLM9XGG6VKS`。
- 提供无副作用的 `--dry-run`、显式 Windows 协议接受 `--yes`、可复用 Python 安装计划/API、已有安装检查及安装后包管理器回读。
- 不自动登录、启动应用、升级已有安装或迁移 Codex 数据；Linux preview 提供官方指引而不执行系统级安装。

## 0.2.15

### Added
- Add Windows compatibility coverage for uv, Node.js, Docker, MySQL, Gitea service guards, and FRP ZIP extraction.
- Expand CI to run the full test/build/docs contract on both `ubuntu-latest` and `windows-latest` for Python 3.10/3.11/3.12.

### Changed
- Add shared platform helpers so private-file chmod, executable chmod, venv paths, and `.exe` command names behave correctly on Windows without regressing POSIX paths.
- Reuse existing Windows Node.js/npm and Docker Desktop installations instead of attempting nvm, group, or systemd setup.
- Use the official PowerShell uv installer and Windows venv activation hints when running on Windows.

### Fixed
- Make setup commands avoid POSIX-only permission calls on Windows and return clear systemd/unsupported-platform errors where a feature remains Linux-only.
- Add Windows-aware MySQL ZIP asset selection, TCP client config, NGINX/Twikoo `.exe` binary paths, Cursor Agent `.cmd` file-wrapper support, and FRP Windows ZIP extraction.

## 0.2.14

### Fixed
- Supersede `0.2.13` by fully hardening `chatup codex -e <profile>` profile isolation: selected env/profile files are loaded without process-environment interpolation, unsafe profile names with path traversal are rejected, and interactive prompt defaults stay inside the selected profile.
- Write Codex `auth.json` through an atomic private-file replacement to avoid a permissive-mode window for `OPENAI_API_KEY`.

## 0.2.13

### Fixed
- Keep `chatup codex -e <profile>` isolated to the explicitly selected ChatEnv OpenAI profile; it no longer silently mixes process-environment credentials or an existing Codex key when a profile is selected.
- Default newly written Codex config to `gpt-5.5`.

## 0.2.12

### Added
- Add top-level `chatup --tree-brief` output from the same registered command surface as `--tree`.

### Changed
- Replace the package-local CLI tree renderer with ChatStyle `add_tree_option()` and explicitly name the root command `chatup`.
- Require `chatstyle>=0.2.0,<0.3.0` and `chatenv>=0.2.10,<0.3.0`, with bounded Click and documentation dependencies.
- Keep explicitly selected ChatEnv service profiles isolated from process-environment credentials.
- Expand CI and release checks to cover installed full/brief trees, wheel and sdist builds, and Twine validation.

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
