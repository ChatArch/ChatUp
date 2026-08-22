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

## Base Commands

| Command | Current capability |
|---|---|
| `chatup doctor` | Check that ChatUp is callable. |
| `chatup uv` | Install `uv` and create the ChatArch Python runtime. |
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
| `chatup hermes` | Install Hermes Agent and optional Hermes WebUI. |
| `chatup cc-connect` | Install the CC Connect CLI and runtime dependencies. |
| `chatup lark-cli` | Configure the official lark-cli and reuse ChatEnv Feishu/Lark config. |

## Codex Command Contract

`chatup codex` configures the OpenAI Codex CLI (`~/.codex/config.toml` and `~/.codex/auth.json`):

- `-e, --env VALUE` is the credential source: a file path is read as an env file; otherwise `VALUE` is treated as a ChatEnv `OpenAI` profile name.
- When `-e PROFILE` selects a ChatEnv profile, ChatUp reads only that explicit profile and does not backfill missing secrets from the active profile, existing Codex config, or process environment.
- If the selected profile lacks `OPENAI_API_KEY`, non-interactive setup fails instead of writing a different account's key.
- Codex CLI 0.144+ requires `wire_api = "responses"`; `chatup codex` writes the CRS/OpenAI-compatible provider with the responses wire API.
- Verify a model channel through Codex itself, for example `chatup codex -e apple -I` followed by `codex exec ...`; direct curl success is not enough for Codex routing.

Common forms:

```bash
chatup codex -e apple -I
chatup codex -e ~/.chatarch/envs/OpenAI/.env -I
chatup codex --api-key "$OPENAI_API_KEY" --base-url https://example.invalid/openai/v1 --model gpt-5.5 -I
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

ChatUp exposes neither a generic `browser` group nor the ambiguous `chrome` command:

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
