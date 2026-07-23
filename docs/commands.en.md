# Command Reference

This page lists the currently implemented first-level `chatup` commands. Runtime help from `chatup <command> --help` is authoritative.

## CLI Tree

ChatUp currently uses a first-level command structure. There is no `chatup setup ...` subtree; installation, initialization, and configuration capabilities are exposed directly under `chatup`:

```text
chatup
|-- doctor
|-- uv
|-- workspace
|-- nodejs
|-- docker
|-- zsh
|-- chrome
|-- frp
|-- gitea
|-- mysql
|-- nginx
|-- crs
|-- cc-connect
|-- claude
|-- codex
|-- opencode
|-- hermes
`-- lark-cli
```

## Base Commands

| Command | Current capability |
|---|---|
| `chatup doctor` | Check that ChatUp is callable. |
| `chatup uv` | Install `uv` and create the ChatArch Python runtime. |
| `chatup nodejs` | Install nvm and the default LTS Node.js. |
| `chatup docker` | Check the Docker environment and show sudo guidance when needed. |
| `chatup zsh` | Configure zsh, oh-my-zsh, plugins, theme, and shell aliases. |
| `chatup chrome` | Install Chrome and Chromedriver. |
| `chatup frp` | Install FRP Client/Server. |

## Agents and Toolchains

| Command | Current capability |
|---|---|
| `chatup claude` | Configure Claude Code CLI and config files. |
| `chatup codex` | Configure Codex CLI and config files. |
| `chatup opencode` | Configure OpenCode CLI and config files. |
| `chatup hermes` | Install Hermes Agent and optional Hermes WebUI. |
| `chatup cc-connect` | Install the CC Connect CLI and runtime dependencies. |
| `chatup lark-cli` | Configure the official lark-cli and reuse ChatEnv Feishu/Lark config. |

## Local Services

| Command | Current capability |
|---|---|
| `chatup gitea` | Install ChatArch Gitea from `ChatArch/gitea` release assets; defaults to latest and can generate a ChatTea-compatible `app.ini` plus user-level systemd service. |
| `chatup mysql` | Install and prepare a ChatData-compatible user-level MySQL runtime, instance layout, `my.cnf`, and optional user-level systemd service. |
| `chatup nginx` | Prepare a user-level NGINX runtime/config/log/run/temp layout under `~/.chatarch/nginx`, and also render reverse-proxy, HTTPS proxy, WebSocket proxy, static root, and redirect templates. |
| `chatup crs` | Install local Claude Relay Service with Redis, config, secrets, admin SPA, and smoke checks. |

## Workspace

| Command | Current capability |
|---|---|
| `chatup workspace` | Initialize the ChatArch human-AI collaboration workspace. |

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
