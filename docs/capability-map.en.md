# ChatUp CLI Capability Map

This page is the concise capability map for the current ChatUp CLI. Use it to check which machine bootstrap, local-service, and agent-toolchain workflows have first-class commands, and which boundaries still belong to sibling projects or system operations.

For complete options, default paths, and command contracts, see [Command Reference](commands.md). For the new-machine path, see [Quick Start](quickstart.md).

## Top-level Commands

```text
chatup
|-- doctor      # Check that ChatUp is callable
|-- uv          # Install uv and create the default ChatArch Python runtime
|-- workspace   # Initialize the ChatArch workspace scaffold
|-- nodejs      # Install nvm and the default LTS Node.js
|-- docker      # Check Docker and show sudo guidance when needed
|-- zsh         # Configure zsh / oh-my-zsh / plugins / aliases
|-- chrome      # Install ChatArch-internal Chrome for Testing
|-- frp         # Install FRP Client/Server
|-- gitea       # Install ChatTea-compatible Gitea runtime/config/service
|-- mysql       # Install ChatData-compatible MySQL runtime/instance/service
|-- nginx       # Prepare user-level NGINX runtime and entry templates
|-- crs         # Install local Claude Relay Service + Redis + smoke check
|-- cc-connect  # Install CC Connect CLI and runtime dependencies
|-- claude      # Configure Claude Code CLI and config files
|-- codex       # Configure Codex CLI and config files
|-- opencode    # Configure OpenCode CLI and config files
|-- hermes      # Install Hermes Agent and optional WebUI
`-- lark-cli    # Configure official lark-cli with ChatEnv Feishu config
```

## Capability Groups

<div class="grid cards" markdown>

- **Base Runtime**

    `uv`, `nodejs`, `docker`, `zsh`, `chrome`, and `frp` prepare common dependencies for a new machine. `doctor` is the minimum health check.

- **Local Services**

    `gitea`, `mysql`, `nginx`, and `crs` prepare common ChatArch local services with user-level defaults under `~/.chatarch/...`.

- **Agent Toolchains**

    `claude`, `codex`, `opencode`, `hermes`, `cc-connect`, and `lark-cli` configure model CLIs, agent runtimes, and Feishu/Lark tooling.

- **Workspace Scaffold**

    `workspace` creates the ChatArch workspace directories such as `AGENTS.md`, `projects/`, `core/`, `skills/`, and `public/`.

</div>

## Base Runtime

```text
chatup doctor              # Check that the CLI is callable
chatup uv                  # Install/reuse uv and create ~/.chatarch/venv
chatup nodejs              # Install nvm and the default LTS Node.js
chatup docker              # Check Docker daemon and current-user permissions
chatup zsh                 # Configure zsh / oh-my-zsh / plugins / aliases
chatup chrome              # Install versioned Chrome for Testing under ~/.chatarch/chrome
chatup frp                 # Install FRP Client/Server
```

These commands only prepare the dependencies ChatArch commonly needs. They are not a general-purpose OS package-management layer. `chatup chrome` additionally exposes a machine-readable descriptor for consumers such as ChatPost, while profiles/accounts remain consumer-owned.

## Local Services

```text
chatup gitea               # Align with ChatTea binary/work path/config/service
chatup mysql               # Align with ChatData runtime/instance/service
chatup nginx               # Prepare ~/.chatarch/nginx runtime/config/log/run/temp
chatup crs                 # Prepare local CRS, Redis, secrets, admin SPA, and smoke check
```

Local-service commands use user-level layouts by default:

| Command | Default directory | Runtime boundary |
| --- | --- | --- |
| `chatup gitea` | `~/.chatarch/chattea` | Gitea binds to `127.0.0.1:3000` by default; public entry belongs to NGINX/public-entry. |
| `chatup mysql` | `~/.chatarch/chatdata` | MySQL binds to `127.0.0.1:3307` by default and can create a user-level service. |
| `chatup nginx` | `~/.chatarch/nginx` | Does not write `/etc/nginx` or reload system services; can render entry templates. |
| `chatup crs` | `~/.chatarch/crs/local` | Local CRS + Redis + smoke check with restricted secret-file permissions. |

## Agent Toolchains

```text
chatup claude              # Configure Claude Code CLI and config files
chatup codex               # Configure Codex CLI and config files
chatup opencode            # Configure OpenCode CLI and config files
chatup hermes              # Install Hermes Agent and optional WebUI
chatup cc-connect          # Install CC Connect CLI and runtime dependencies
chatup lark-cli            # Configure official lark-cli with ChatEnv Feishu config
```

These commands prepare local CLIs and config files. Provider accounts, tokens, workflow permissions, and platform policies remain owned by the corresponding tool or ChatEnv.

## Workspace

```text
chatup workspace default ~/Playground  # Initialize the ChatArch workspace
```

`workspace` creates and syncs directories and conventions. It does not replace project repo initialization, task PRDs, progress records, or review workflows. See [Workspace Scaffold](workspace.md).

## Out of Scope

- No system-level service orchestration; defaults do not write `/etc`, modify system NGINX, or create root-level services.
- No general-purpose package-management promise; ChatUp only collects common ChatArch setup flows.
- No secret, token, connection string, or Authorization header echo.
- No planned commands in the formal CLI tree; future capabilities belong in a roadmap or PRD until implemented.
