# Command Reference

This page lists the currently implemented first-level `chatup` commands. Runtime help from `chatup <command> --help` is authoritative.

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
| `chatup gitea` | Install the ChatArch Gitea binary from `ChatArch/gitea` release assets. |
| `chatup crs` | Install local Claude Relay Service with Redis, config, secrets, admin SPA, and smoke checks. |

## Workspace

| Command | Current capability |
|---|---|
| `chatup workspace` | Initialize the ChatArch human-AI collaboration workspace. |

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
