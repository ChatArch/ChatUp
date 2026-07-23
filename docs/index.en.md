# ChatUp Documentation

ChatUp is the standalone ChatArch setup CLI. It prepares a machine for ChatArch workflows through reviewable, testable first-level setup commands.

It is not a general-purpose package manager. Its job is to capture ChatArch's common machine bootstrap and local service setup steps in a stable CLI surface.

## Use Cases

- New machine bootstrap: install Python, Node.js, and other base runtimes.
- Workspace initialization: generate the human-AI collaboration workspace scaffold.
- Agent toolchain setup: configure Claude Code, Codex, OpenCode, Hermes, CC Connect, and related tools.
- Local services: install ChatArch Gitea, ChatData-compatible MySQL, Claude Relay Service, FRP, and other local components, prepare user-level NGINX, and generate entry templates.

## Boundaries

- ChatUp handles installation, initialization, and local configuration; it does not own long-running orchestration.
- ChatUp can write local config and secret files, but it must not print sensitive values.
- Interactive commands follow the shared `-i` / `-I` convention: `-i` forces prompts and `-I` disables prompts with fast failures.
- Service setup commands prefer safe local defaults such as `127.0.0.1`, task-local directories, and restrictive file permissions.

## Documentation

- [Quick Start](quickstart.md)
- [Command Reference](commands.md)
- [Workspace Scaffold](workspace.md)
