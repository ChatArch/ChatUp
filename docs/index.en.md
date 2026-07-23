# ChatUp Documentation

ChatUp is the standalone ChatArch setup CLI. It prepares a machine for ChatArch workflows through reviewable, testable first-level setup commands.

It is not a general-purpose package manager. Its job is to capture ChatArch's common machine bootstrap and local service setup steps in a stable CLI surface.

## Primary Entry Points

<div class="grid cards" markdown>

- **Quick Start**

    Start with editable install, `chatup doctor`, `chatup uv`, and workspace initialization to verify a local machine.

    [Open Quick Start](quickstart.md)

- **Command Reference**

    Read the annotated CLI tree, command groups, service install defaults, and local safety contracts.

    [Open Command Reference](commands.md)

- **Workspace Scaffold**

    Understand the ChatArch workspace layout created by `chatup workspace` and its project-record conventions.

    [Open Workspace Guide](workspace.md)

</div>

## Use Cases

<div class="grid cards" markdown>

- **New Machine Bootstrap**

    Install Python, Node.js, Docker checks, Chrome/Chromedriver, and shell basics.

- **Workspace Initialization**

    Generate the human-AI collaboration workspace with `projects/`, `core/`, `skills/`, and `public/`.

- **Agent Toolchain Setup**

    Configure Claude Code, Codex, OpenCode, Hermes, CC Connect, and Feishu/Lark tooling.

- **Local Services**

    Install ChatArch Gitea, ChatData-compatible MySQL, Claude Relay Service, FRP, prepare user-level NGINX, and generate entry templates.

</div>

## Safety Defaults

<div class="grid cards" markdown>

- **Local First**

    Service commands bind to `127.0.0.1` by default; public entry belongs to NGINX/public-entry.

- **ChatArch Home**

    New install targets default to `~/.chatarch/...` instead of system directories.

- **No Secret Echo**

    ChatUp can write local config and secret files, but it must not print sensitive values.

</div>

## Boundaries

- ChatUp handles installation, initialization, and local configuration; it does not own long-running orchestration.
- Interactive commands follow the shared `-i` / `-I` convention: `-i` forces prompts and `-I` disables prompts with fast failures.
- Service setup commands prefer safe local defaults such as `127.0.0.1`, task-local directories, and restrictive file permissions.
