# ChatUp Documentation

ChatUp is the standalone ChatArch setup CLI. It prepares a machine for ChatArch workflows through reviewable, testable first-level setup commands.

It is not a general-purpose package manager. Its job is to capture ChatArch's common machine bootstrap and local service setup steps in a stable CLI surface.

Site entry: https://arch.gh.wzhecnu.cn/ChatUp/en/

## Choose Documentation by Scenario

| Scenario | Document |
| --- | --- |
| Verify ChatUp, the Python runtime, and a workspace on a new machine | [Quick Start](quickstart.md) |
| Read the complete top-level tree and independent CFT/ChromeDriver contracts | [CLI Tree](cli-tree.md) |
| Read command groups, option boundaries, and service defaults | [Command Reference](commands.md) |
| Check which ChatArch setup flows have first-class commands | [CLI Capability Map](capability-map.md) |
| Understand the directories and project-record conventions created by `chatup workspace` | [Workspace Scaffold](workspace.md) |
| Install ChatTea-compatible Gitea, ChatData-compatible MySQL, user-level NGINX, and CRS | [Command Reference: Local Services](commands.md#local-services) |
| Confirm ChatArch default paths, safety boundaries, and interactive conventions | [CLI Capability Map: Out of Scope](capability-map.md#out-of-scope) |

## Documentation Organization

The docs are organized by task and capability so the site does not collapse into one linear setup checklist:

- **Getting started**: install ChatUp, run `doctor`, create the Python runtime, and initialize a workspace.
- **CLI / capability map**: list implemented commands, command groups, and current boundaries.
- **Local services**: explain user-level defaults for Gitea, MySQL, NGINX, and CRS.
- **Workspace**: explain the ChatArch workspace scaffold and project-record layout.
- **Safety boundary**: explain local listeners, secret files, `~/.chatarch/...` defaults, and system-level out-of-scope areas.

## Primary Entry Points

<div class="grid cards" markdown>

- **Quick Start**

    Start with editable install, `chatup doctor`, `chatup uv`, and workspace initialization to verify a local machine.

    [Open Quick Start](quickstart.md)

- **Command Reference**

    Read the annotated CLI tree, command groups, service install defaults, and local safety contracts.

    [Open Command Reference](commands.md)

- **CLI Tree**

    Inspect every first-level command and the independent CFT/ChromeDriver install, JSON output, and Python descriptor contracts.

    [Open CLI Tree](cli-tree.md)

- **CLI Capability Map**

    Like ChatTea's capability map, this page checks first-class commands, default directories, and out-of-scope boundaries by responsibility.

    [Open Capability Map](capability-map.md)

- **Workspace Scaffold**

    Understand the ChatArch workspace layout created by `chatup workspace` and its project-record conventions.

    [Open Workspace Guide](workspace.md)

</div>

## Use Cases

<div class="grid cards" markdown>

- **New Machine Bootstrap**

    Install Python, Node.js, Docker checks, independent Chrome for Testing/ChromeDriver backends, and shell basics.

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

## CLI

```bash
chatup --help
chatup chrome-for-testing --help
chatup chromedriver --help
chatup gitea --help
chatup mysql --help
chatup nginx --help
```

See [CLI Tree](cli-tree.md) for the complete first-level tree, [Command Reference](commands.md) for detailed contracts, and [CLI Capability Map](capability-map.md) for the concise responsibility map.

## Boundaries

- ChatUp handles installation, initialization, and local configuration; it does not own long-running orchestration.
- Interactive commands follow the shared `-i` / `-I` convention: `-i` forces prompts and `-I` disables prompts with fast failures.
- Service setup commands prefer safe local defaults such as `127.0.0.1`, task-local directories, and restrictive file permissions.
