# Command Reference

This page lists the currently implemented first-level `chatup` commands. Runtime help from `chatup <command> --help` is authoritative.

## CLI Tree

ChatUp currently uses a first-level command structure. There is no `chatup setup ...` subtree; installation, initialization, and configuration capabilities are exposed directly under `chatup`:

```text
chatup
|-- doctor      # Check that ChatUp is callable
|-- uv          # Install uv and create the default ChatArch Python runtime
|-- workspace   # Initialize the ChatArch workspace scaffold
|-- nodejs      # Install nvm and the default LTS Node.js
|-- docker      # Check Docker and show sudo guidance when needed
|-- zsh         # Configure zsh / oh-my-zsh / plugins / aliases
|-- chrome              # Install regular Google Chrome for the current OS
|-- iterm               # Install iTerm2 (macOS only)
|-- macos               # Select supported macOS apps, including Blender on Apple Silicon
|-- remotion            # Initialize a locked local video project
|-- chrome-for-testing # Manage Google Chrome for Testing browsers
|-- chromedriver       # Manage ChromeDriver WebDriver servers
|-- playwright         # Manage Playwright packages and Chromium browsers
|-- frp         # Install FRP Client/Server
|-- gitea       # Install ChatTea-compatible Gitea runtime/config/service
|-- discourse   # Prepare Discourse config and ChatEnv-managed admin credentials
|-- zulip       # Prepare Zulip Compose and ChatEnv-managed admin credentials
|-- mysql       # Install ChatData-compatible MySQL runtime/instance/service
|-- twikoo      # Install multi-instance Twikoo runtime/instance/service
|-- nginx       # Prepare user-level NGINX runtime and entry templates
|-- crs         # Install local Claude Relay Service + Redis + smoke check
|-- cc-connect  # Install CC Connect CLI and runtime dependencies
|-- claude      # Configure Claude Code CLI and config files
|-- chatgpt      # Install the new ChatGPT desktop app (includes Codex)
|-- codex       # Configure Codex CLI and config files
|-- cursor-agent # Configure Cursor Agent CLI auth and config files
|-- opencode    # Configure OpenCode CLI and config files
|-- hermes      # Install Hermes Agent and optional WebUI
`-- lark-cli    # Configure official lark-cli with ChatEnv Feishu config
```

## Command Group Overview

<div class="grid cards" markdown>

- **Base Runtime**

    `doctor`, `uv`, `nodejs`, `docker`, `zsh`, `chrome-for-testing`, `chromedriver`, `playwright`, and `frp` prepare and check machine-level runtime basics.

- **Local Services**

    `gitea`, `discourse`, `zulip`, `mysql`, `twikoo`, `nginx`, and `crs` prepare common ChatArch local services under `~/.chatarch/...` by default. Discourse/Zulip admin credentials come from ChatEnv profiles or env files.

- **Agent Toolchains**

    `claude`, `codex`, `cursor-agent`, `opencode`, `hermes`, `cc-connect`, and `lark-cli` configure model, agent, and Feishu/Lark tooling.

- **Workspace**

    `workspace` creates the ChatArch human-AI collaboration layout and project-record entry points.

</div>

## Windows Compatibility

- `chatup uv` uses the official PowerShell installer on Windows and prints the `Scripts/Activate.ps1` activation hint.
- `chatup nodejs` reuses `node`/`npm` already on PATH on Windows instead of writing nvm shell init; when missing, it points users to the official installer, winget, or nvm-windows.
- `chatup docker` checks Docker Desktop's `docker`/`docker compose` on Windows and skips Unix group/systemd checks.
- `chatup mysql` selects the MySQL Windows ZIP asset, `.exe` binary names, and TCP client config; `gitea`/`mysql`/`twikoo`/`nginx` `--service` flows still require user-level systemd and fail clearly on Windows.
- `chatup cursor-agent --credential-store file-wrapper` writes `.cmd` wrappers on Windows; `chatup frp` supports Windows ZIP release assets; `zsh` and `crs` remain POSIX/Linux-only setup flows.

## Base Commands

| Command | Current capability |
|---|---|
| `chatup doctor` | Check that ChatUp is callable. |
| `chatup uv` | Install `uv` and create the ChatArch Python runtime; `--activate / --no-activate` controls existing Bash/Zsh startup updates (enabled by default). See [Quick Start](quickstart.md). |
| `chatup nodejs` | Install nvm and the default LTS Node.js. |
| `chatup docker` | Check the Docker environment and show sudo guidance when needed. |
| `chatup zsh` | Configure zsh, oh-my-zsh, plugins, theme, and shell aliases. |
| `chatup chrome-for-testing` | Independently manage Google Chrome for Testing browsers and JSON/Python descriptors. |
| `chatup chromedriver` | Independently manage ChromeDriver WebDriver servers and match CFT/browser versions. |
| `chatup playwright` | Install an exact Playwright package plus its managed Chromium and return a reusable descriptor. |
| `chatup frp` | Install FRP Client/Server. |

## Agents and Toolchains

| Command | Current capability |
|---|---|
| `chatup claude` | Configure Claude Code CLI and config files. |
| `chatup codex` | Configure Codex CLI and config files. |
| `chatup cursor-agent` | Install/verify Cursor Agent CLI and safely copy `auth.json`, `cli-config.json`, and `agent-cli-state.json`. |
| `chatup opencode` | Configure OpenCode CLI and config files. |
| `chatup hermes` | Install Hermes Agent and optional Hermes WebUI; fall back to `gpt-5.6-terra` only when no model is configured. Explicit models, profiles, existing config and environment values retain precedence. |
| `chatup cc-connect` | Install the CC Connect CLI and runtime dependencies. |
| `chatup lark-cli` | Configure the official lark-cli and reuse ChatEnv Feishu/Lark config. |

## macOS Apps {#macos}

`chatup macos` is macOS-only. Apple Silicon offers Snipaste, iTerm2, Google Chrome and Blender, all selected by default; Intel retains the first three apps.

```bash
chatup macos
chatup macos --app snipaste
chatup macos --app iterm --app chrome
chatup macos --app blender
chatup macos -I
chatup macos --dry-run
chatup macos -i --dry-run
```

| Option / context | Behavior |
| --- | --- |
| Terminal without `--app` | Show all supported apps checked; Space toggles, Enter confirms, Ctrl-C cancels. Deselecting everything exits successfully without installation. |
| `--app snipaste\|iterm\|chrome\|blender` | Install only the named apps; repeat to select several. Duplicates are removed and no prompt appears by default. Blender requires Apple Silicon. |
| `-i` | Force the menu, using explicit `--app` values as preselection; fail before installation if no terminal is available. |
| `-I`, no terminal, or `CHATARCH_AUTO_PROMPT=0` | Skip prompts and install explicit selections, or every app supported on the current architecture. |
| `--dry-run` | Skip automatic prompting and preview selected sources/paths. Add `-i` to choose first. No network, installer execution, or directory writes. |
| `--log-level DEBUG\|INFO\|WARNING\|ERROR` | Set installer logging; defaults to `INFO`. |

Snipaste uses the [macOS DMG download](https://dl.snipaste.com/mac) linked by its [official website](https://www.snipaste.com/). Apps share the [native macOS install flow](#chrome-iterm), without Homebrew: verify bundle identity and official publisher signature, then install to `/Applications`, falling back to `~/Applications` if needed. Existing apps are verified and reused, without automatic upgrades or launch. Users grant Snipaste's screen-capture permissions through macOS when first needed.

Blender uses the pinned [official 5.2.2 LTS Apple Silicon DMG](https://download.blender.org/release/Blender5.2/blender-5.2.2-macos-arm64.dmg), checked against its [official SHA-256](https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256) before mounting, followed by version, publisher signature and Gatekeeper notarization checks. Existing Blender installations are verified and preserved, without overwrites or downgrades. Explicit Blender selection on Intel fails before installing any selected app; Intel installation is not implemented in this release.

Apps install sequentially in selection order. An error stops subsequent installations; earlier successes remain and are reused on the next run. Other operating systems fail before installation, even when only Chrome is selected.

## Remotion Video Projects {#remotion}

`chatup remotion PROJECT_DIR` creates a Remotion 4.0.530 / React 19.1.0 project with a complete npm lockfile and a renderable 3-second 720p example. Existing Node.js >=18.12 and npm >=9 are checked before installation; the system runtime is not replaced.

```bash
chatup remotion ./my-video --dry-run -I
chatup remotion ./my-video -I
chatup remotion ./my-video -I  # Verify the existing project and preserve source edits
chatup remotion ./my-video --browser-executable /path/to/chrome -I
cd my-video
npm run studio
npm run render -- --browser-executable='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
```

Without a directory, a terminal prompt suggests `remotion-video` under the current directory. An explicit directory skips automatic prompting. `-i` forces the prompt; `-I` disables it. Missing input fails without a terminal or when `CHATARCH_AUTO_PROMPT=0`. `--dry-run` only previews: no Node/npm execution, network requests or directory creation. `--log-level` accepts `DEBUG|INFO|WARNING|ERROR`, defaulting to `INFO`.

New projects are staged beside the target. ChatUp runs `npm ci --ignore-scripts --include=optional --no-audit --no-fund`, verifies the four direct dependency versions and then renames the project into place. Dependencies stay local and their lifecycle scripts do not run. Failures clean staging. Existing unrelated directories, files and symlink targets are rejected. The `.chatup-remotion.json` marker identifies managed projects; repeated runs verify them without reinstalling dependencies or replacing source edits. Missing or changed dependencies cause an error for the user to repair inside the project, never an automatic overwrite.

Initialization detects local Chrome/Chromium or accepts `--browser-executable PATH`, then prints the corresponding render command. It does not start Studio or download browsers. A missing browser does not prevent project creation; the output recommends `chatup chrome` before rendering. Running Remotion render without an explicit browser can trigger Remotion's own browser download. On supported Macs, `chatup macos --app chrome --app blender` prepares desktop tools; Remotion belongs in its own project directory.

Real installation and MP4 rendering were verified on Apple Silicon macOS with Node 24.21.0 and npm 11.19.0. Other systems use the same Node/npm project flow, but native installation and rendering have not been exercised on every platform.

## Chrome and iTerm2 {#chrome-iterm}

`chatup chrome` installs regular Google Chrome. `chatup iterm` installs iTerm2 on macOS only.

| Platform | Chrome installation | iTerm2 |
| --- | --- | --- |
| macOS Intel / Apple Silicon | Google's official universal stable DMG, no Homebrew needed | Official stable ZIP |
| Windows | Exact WinGet package `Google.Chrome`, silent installation | Unsupported, exits with an error |
| Linux x86_64 | Official stable DEB (apt-get) or RPM (dnf/yum/zypper) | Unsupported, exits with an error |
| Linux ARM / other systems | Explicit unsupported-platform error | Unsupported |

```bash
chatup chrome
chatup iterm
chatup chrome --dry-run
chatup iterm --dry-run
chatup chrome --sudo --yes   # Linux: allow sudo and package confirmation
chatup chrome --yes          # Windows: accept source and package agreements
```

Both commands accept `--log-level DEBUG|INFO|WARNING|ERROR`. There are no required inputs or input prompts. `--dry-run` only reads local platform/paths and prints the plan, without network requests, installer processes or directory writes.

macOS reuses existing apps in `/Applications` or `~/Applications`. New apps go to writable `/Applications`, falling back to `~/Applications`. Downloads are checked for bundle ID, version, executable, minimum macOS version and official Developer ID signature, then copied into staging and renamed into place. Invalid existing apps cause an error and are not overwritten. Commands do not upgrade, launch, log in, or change browser/terminal defaults. Temporary downloads use `~/.chatarch/cache/desktop` (respecting `CHATARCH_HOME`); staging is cleaned and DMGs detached afterward.

Linux needs a supported package manager. Non-root users must explicitly pass `--sudo`; otherwise installation stops with instructions. Root may install directly. The package manager resolves dependencies/system requirements, and `google-chrome --version` verifies the result. Windows requires [WinGet](https://aka.ms/getwinget); exact package records are checked before and after installation, without upgrading existing Chrome.

Desktop installers do not write CFT/ChromeDriver/Playwright metadata, browser profiles or cookies. Automation artifacts retain their independent backends.

Sources: [Google Chrome](https://www.google.com/chrome/), [iTerm2 downloads](https://iterm2.com/downloads.html).

## ChatGPT Desktop App {#chatgpt-desktop}

`chatup chatgpt` installs the official new ChatGPT desktop app, including Codex. It is separate from `chatup codex` (the Codex CLI), and does not install ChatGPT Classic or the deprecated `codex-app` cask.

| Platform | Install source | Prerequisites |
| --- | --- | --- |
| macOS | `brew install --cask homebrew/cask/chatgpt` | Existing [Homebrew](https://brew.sh/); the current cask checks OS and CPU requirements |
| Windows | `winget install --id 9PLM9XGG6VKS --exact --source msstore` | WinGet on PATH and Microsoft Store access |
| Linux | [Official Linux preview instructions](https://learn.chatgpt.com/docs/linux/linux-app) | Not automated by ChatUp; no sudo, repository configuration or full-system upgrade |

```bash
chatup chatgpt --dry-run  # Show the current OS install command; no network/download
chatup chatgpt            # Install the desktop app
chatup chatgpt --yes      # Windows: explicitly accept Store source/package agreements
```

Windows installation is non-interactive. Use `--yes` when first-time Store agreements need acceptance. This flag does not change macOS behavior. Missing package managers produce installation guidance instead of bootstrapping Homebrew/WinGet. A package-manager-registered installation is skipped, not upgraded (`--no-upgrade` on Windows). A registered legacy `1.x` ChatGPT Classic cask produces a manual-migration error instead of reporting the new app as installed. Conflicts with manually installed apps remain package-manager errors; ChatUp does not force an overwrite.

Success means the package manager installation record was read back, not that the app was launched or authenticated. Homebrew/Microsoft Store and the official app own application paths, caches and runtime data using native layouts (typically `/Applications/ChatGPT.app` on macOS), rather than ChatArch service directories. ChatUp does not write desktop login state or change Codex CLI configuration. Open ChatGPT and sign in manually after installation.

Call the Python API without shelling out to the CLI:

```python
from chatup.setup.chatgpt import plan_chatgpt_install, setup_chatgpt

plan = plan_chatgpt_install()  # Pure plan; no package manager required
result = setup_chatgpt(dry_run=True)
# Actual installation: setup_chatgpt(yes=True)
```

Results include `app`, `platform`, `manager`, `package`, `command`, and `verify_command`. The install API adds `status` (`planned` / `already_installed` / `installed`) and `verified`. Failures/timeouts raise `RuntimeError` and produce a nonzero CLI exit. Check package-manager state before retrying after a timeout.

Sources: [OpenAI downloads](https://chatgpt.com/download/), [official Windows instructions](https://learn.chatgpt.com/docs/windows/windows-app), [Homebrew ChatGPT](https://formulae.brew.sh/cask/chatgpt).

## Codex Command Contract

`chatup codex` configures the OpenAI Codex CLI (`~/.codex/config.toml` and `~/.codex/auth.json`):

The fallback model is `gpt-5.6-terra` (GPT-5.6 Terra), used only when no model is configured. An explicit `--model`, the selected OpenAI profile, and (when no profile is selected) existing Codex config, process environment and the active profile retain their existing precedence. User-configured models are not forcibly replaced by the fallback.

- `-e, --env VALUE` is the credential source: a file path is read as an env file; otherwise `VALUE` is treated as a ChatEnv `OpenAI` profile name.
- When `-e PROFILE` selects a ChatEnv profile, ChatUp reads only that explicit profile. It does not backfill missing secrets from the active profile, an existing Codex config, or process environment variables. Profile files are loaded without interpolation; unresolved `${...}` references fail instead of falling back to the process environment.
- ChatEnv profile names cannot contain path separators, `.` or `..`; pass an existing file path when file-based config is intended.
- If the selected profile lacks `OPENAI_API_KEY`, non-interactive setup fails instead of writing a different account's key.
- Codex CLI 0.144+ requires `wire_api = "responses"`; `chatup codex` writes the CRS/OpenAI-compatible provider with the responses wire API.
- Verify a model channel through Codex itself, for example `chatup codex -e apple -I` followed by `codex exec ...`; direct curl success is not enough for Codex routing.

Common forms:

```bash
chatup codex -e apple -I
chatup codex -e ~/.chatarch/envs/OpenAI/.env -I
chatup codex --api-key "$OPENAI_API_KEY" --base-url https://example.invalid/openai/v1 --model gpt-5.6-terra -I
```

## Cursor Agent Command Contract

`chatup cursor-agent` targets the Cursor Agent CLI, not the Cursor IDE GUI:

- `--auth-json PATH` copies Cursor `auth.json` with `accessToken` / `refreshToken`;
- `--auth-env PATH` reads `CURSOR_ACCESS_TOKEN` and `CURSOR_REFRESH_TOKEN` from an env file and writes Cursor JSON;
- `-e, --env VALUE` is the fast credential source: a file path is read as an env file, otherwise `VALUE` is treated as a ChatEnv `CursorAgent` profile name;
- `--env-profile NAME` reads tokens from a ChatEnv `CursorAgent` profile and writes Cursor JSON;
- `--save-profile NAME` saves imported tokens to a ChatEnv `CursorAgent` profile without printing secret values;
- `--cli-config PATH` copies `~/.cursor/cli-config.json`;
- `--agent-state PATH` copies `~/.cursor/agent-cli-state.json`;
- `--api-key-env NAME` uses the named environment variable as `CURSOR_API_KEY` only during verification, avoiding secrets in argv;
- `--credential-store file-wrapper` writes a token-free `cursor-agent` wrapper that reads `auth.json` at runtime and uses file-backed auth, useful when migrating Linux `auth.json` to macOS;
- Cursor's own login/config files are written with restrictive permissions; ChatEnv `CursorAgent` profiles are left to ChatEnv's native storage mechanism, and ChatUp does not chmod profile `.env` files.

Common forms:

```bash
chatup cursor-agent --install-only -I
chatup cursor-agent --auth-json ./auth.json --cli-config ./cli-config.json --agent-state ./agent-cli-state.json --credential-store file-wrapper -I
chatup cursor-agent -e ./cursor.env --credential-store file-wrapper -I
chatup cursor-agent --auth-env ./cursor.env --save-profile work --credential-store file-wrapper -I
chatup cursor-agent -e work --credential-store file-wrapper -I
```

## Local Services

| Command | Current capability |
|---|---|
| `chatup gitea` | Install ChatArch Gitea from `ChatArch/gitea` release assets; defaults to latest and can generate a ChatTea-compatible `app.ini` plus user-level systemd service. |
| `chatup discourse` | Prepare `~/.chatarch/discourse` Discourse Docker/app.yml layout and write ChatEnv-managed `DISCOURSE_ADMIN_USERNAME`, `DISCOURSE_ADMIN_EMAIL`, and `DISCOURSE_ADMIN_PASSWORD` to a restricted `secrets/admin.env`. |
| `chatup zulip` | Prepare `~/.chatarch/zulip` Zulip Docker Compose, bind-mounted data directories, secret files, and ChatEnv-managed `ZULIP_ADMIN_USERNAME`, `ZULIP_ADMIN_EMAIL`/`ZULIP_ADMIN_MAIL`, and `ZULIP_ADMIN_PASSWORD`. |
| `chatup mysql` | Install and prepare a ChatData-compatible user-level MySQL runtime, instance layout, `my.cnf`, and optional user-level systemd service. |
| `chatup twikoo` | Install Twikoo from `twikoojs/twikoo` release assets and prepare a multi-instance layout, instance env, instance-local `bin/twikoo`, and optional user-level systemd service. |
| `chatup nginx` | Prepare a user-level NGINX runtime/config/log/run/temp layout under `~/.chatarch/nginx`, and also render reverse-proxy, HTTPS proxy, WebSocket proxy, static root, and redirect templates. |
| `chatup crs` | Install local Claude Relay Service with Redis, config, secrets, admin SPA, and smoke checks. |

## Workspace

| Command | Current capability |
|---|---|
| `chatup workspace` | Initialize the ChatArch human-AI collaboration workspace. |

## Browser Artifact Backend Contract

The regular desktop browser is installed with `chatup chrome`. The managed automation artifacts keep independent backends:

- `chatup chrome-for-testing` manages the launchable Google Chrome for Testing browser under `~/.chatarch/chrome-for-testing` by default;
- `chatup chromedriver` manages the ChromeDriver WebDriver server under `~/.chatarch/chromedriver` by default;
- `chatup playwright` manages an exact Playwright package and Playwright Chromium under `~/.chatarch/playwright` by default;
- Chrome for Testing and ChromeDriver own full artifact lifecycles; Playwright exposes only the task-required `install/path/doctor`;
- Testing in `Chrome for Testing` is the official artifact name, not a user-facing `test` operation;
- `chromium` remains unregistered until a provider is verified;
- installations use official HTTPS manifests, optional SHA-256, bounded ZIP extraction, `installation.json`, and atomic directory replacement;
- `remove` requires `--yes`; `gc` defaults to dry-run and apply also requires `--yes`;
- neither backend modifies system Chrome or creates profile/cookie/account/extension state.

```bash
chatup chrome-for-testing install --channel stable -I
chatup chrome-for-testing path 145.0.7632.6 -I
chatup chromedriver install --match-cft-version 145.0.7632.6 -I
chatup chromedriver doctor 145.0.7632.6 --output json -I
chatup playwright install 1.61.1 --output json -I
chatup playwright path 1.61.1 -I
```

See [CLI Tree](cli-tree.md) for the full subcommand tree, ChatStyle behavior, and Python contract.

## Gitea Command Contract

`chatup gitea` aligns with ChatTea's local Gitea layout:

- Default release: `latest`, resolved from the newest `ChatArch/gitea` GitHub Release.
- Default binary: `~/.chatarch/chattea/bin/gitea`.
- Default work path: `~/.chatarch/chattea/gitea`.
- Optional `--init` writes `custom/conf/app.ini` with `0600` permissions.
- Optional `--service` writes a user-level systemd service.
- Gitea binds to `127.0.0.1:3000` by default; public or local domain entry belongs to NGINX/public-entry.

Common forms:

```bash
chatup gitea --force
chatup gitea --init --service --base-url http://127.0.0.1:3000
chatup gitea --init --database-backend mysql --database-host ~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
```

## MySQL Command Contract

`chatup mysql` reuses the first ChatData no-sudo runtime model:

- Default MySQL version: `8.4.6`.
- Default home: `~/.chatarch/chatdata`.
- Default instance: `default`.
- Default port: `3307`.
- Default bind address: `127.0.0.1`.
- By default it downloads the runtime, initializes the instance layout, writes `my.cnf`, and writes a user-level systemd service, but it does not start the service.
- `--smoke` and `--database` require `--start` to avoid delayed failures when the service is not running.

Common forms:

```bash
chatup mysql
chatup mysql --start --smoke
chatup mysql --start --database gitea
chatup mysql --home ~/.chatarch/chatdata --name default --port 3307
```

## Twikoo Command Contract

`chatup twikoo` targets no-Docker, multi-instance Twikoo comment-service installs:

- Default Twikoo version: `1.7.15`.
- Default repo: `twikoojs/twikoo`.
- Default home: `~/.chatarch/twikoo`.
- Default instance: `chatblog`.
- Default port: `8892`.
- Default bind address: `127.0.0.1`.
- By default it downloads the release binary, initializes the instance layout, writes `env/twikoo.env`, and writes a user-level systemd service, but it does not start the service.
- Each instance starts through `instances/<name>/bin/twikoo`, with `bin/.env` pointing at that instance's own `env/twikoo.env`; do not run multiple instances directly from a shared runtime-adjacent `.env`.
- Local/public domain entry remains the responsibility of NGINX/public-entry.

Common forms:

```bash
chatup twikoo --name chatblog --port 8892
chatup twikoo --name chatblog --port 8892 --start --smoke
chatup twikoo --home ~/.chatarch/twikoo --name another-blog --port 8893 --no-start
```

## NGINX Command Contract

`chatup nginx` prepares user-level NGINX by default instead of changing system NGINX:

- Default home: `~/.chatarch/nginx`.
- Default binary: copy an existing `nginx` into `~/.chatarch/nginx/bin/nginx`; if PATH has no `nginx`, pass `--binary PATH`.
- Default config: `~/.chatarch/nginx/conf/nginx.conf`.
- Default logs/run/temp: `~/.chatarch/nginx/logs`, `~/.chatarch/nginx/run`, and `~/.chatarch/nginx/temp`.
- Default site directories: `~/.chatarch/nginx/conf/sites-available` and `~/.chatarch/nginx/conf/sites-enabled`.
- Default listener: `127.0.0.1:8080`.
- By default it writes a user-level systemd service; it does not write `/etc/nginx` or reload system services.

```bash
chatup nginx
chatup nginx --home ~/.chatarch/nginx --binary /usr/sbin/nginx --port 8080
chatup nginx --start --smoke
```

`chatup nginx` also keeps template rendering mode:

```bash
chatup nginx --list
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup nginx websocket-proxy ./ws.conf --set SERVER_NAME=ws.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup nginx static-root ./site.conf --set SERVER_NAME=site.local.example.invalid --set ROOT_DIR=/srv/site
```

## CRS Command Contract

`chatup crs` targets local development by default:

- Default install directory: `~/.chatarch/crs/local`
- Default CRS port: `12392`
- Default Redis port: `6379`
- Secret file: `.local-secrets.env` under the install directory with restrictive permissions.
- By default it starts the service and runs a smoke check.

Common forms:

```bash
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
chatup crs --no-start --no-smoke
```
