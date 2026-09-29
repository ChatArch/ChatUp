# ChatUp

ChatUp is the standalone ChatArch setup CLI. It carries the former `chattool setup` responsibilities as first-level commands for development runtimes, agent CLIs, workspace scaffolds, and local services. For example, `chattool setup workspace` maps to `chatup workspace`.

- Documentation: <https://arch.gh.wzhecnu.cn/ChatUp/en/>
- Chinese README: [README.md](README.md)
- Source: <https://github.com/ChatArch/ChatUp>

Choose documentation by scenario:

| Scenario | Document |
| --- | --- |
| Verify ChatUp, the Python runtime, and a workspace on a new machine | `docs/quickstart.en.md` |
| Read the complete top-level CLI tree and independent CFT/ChromeDriver/Playwright contracts | `docs/cli-tree.en.md` |
| Read command groups, option boundaries, and service defaults | `docs/commands.en.md` |
| Check which ChatArch setup flows have first-class commands | `docs/capability-map.en.md` |
| Understand the directories and project-record conventions created by `chatup workspace` | `docs/workspace.en.md` |
| Install ChatTea-compatible Gitea, ChatData-compatible MySQL, user-level NGINX, and CRS | `docs/commands.en.md` |

## Quick Start

```bash
chatup --help
chatup --version
chatup --tree
chatup --tree-brief
chatup doctor
chatup uv
chatup chrome-for-testing install --channel stable -I
chatup playwright install 1.61.1 -I
chatup workspace default ~/Playground
```

`chatup uv` updates auto-activation in existing `~/.bashrc` and `~/.zshrc` by default. Use `chatup uv --no-activate` to leave startup configuration unchanged. Missing rc files are not created, and Windows skips this step.

Common install commands:

```bash
chatup gitea --force
chatup mysql
chatup nginx
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## macOS Apps

```bash
chatup macos                       # Choose apps; all four are selected on Apple Silicon
chatup macos --app snipaste         # Install only Snipaste
chatup macos --app blender          # Install Blender 5.2.2 LTS (Apple Silicon)
chatup macos -I                    # Install all supported apps without prompting
chatup macos --dry-run             # Preview the installation plan
```

macOS only. Apple Silicon selects Snipaste, iTerm2, Chrome and Blender by default; Intel retains the first three. In a terminal, use Space to toggle apps and Enter to install; deselecting all apps exits without installation. Repeat `--app snipaste|iterm|chrome|blender` to select several apps. Official downloads require no Homebrew, and verified existing apps are reused. See the [macOS install command](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/#macos).

## Remotion Video Projects

```bash
chatup remotion ./my-video --dry-run -I
chatup remotion ./my-video -I
cd my-video
npm run studio
```

Requires existing Node.js >=18.12 and npm >=9. Creates a locked Remotion 4.0.530 project, detects local Chrome and prints a render command. Existing unrelated directories are protected; Node is not replaced and browsers are not downloaded. Projects live in the specified directory. On supported Macs, `chatup macos --app blender --app chrome` prepares the desktop tools. See the [Remotion setup contract](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/#remotion).

## Chrome and iTerm2

```bash
chatup chrome --dry-run
chatup chrome             # Install regular Google Chrome for the current OS
chatup iterm              # Install iTerm2, macOS only
chatup chrome --sudo --yes # Linux: allow elevation and package confirmation
```

macOS downloads official DMG/ZIP artifacts and verifies publisher signatures, without Homebrew. Apps go to `/Applications`, falling back to `~/Applications` if needed. Windows uses WinGet `Google.Chrome`; Linux x86_64 uses official DEB/RPM packages with apt/dnf/yum/zypper. Existing apps are verified and reused; defaults and profiles are unchanged. Automation browsers remain under `chatup chrome-for-testing`. See the [install contract](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/#chrome-iterm).

## ChatGPT / Codex Desktop App

```bash
chatup chatgpt --dry-run
chatup chatgpt
chatup chatgpt --yes  # Accept first-time Microsoft Store agreements on Windows
```

Installs the official new ChatGPT desktop app including Codex. Requires Homebrew on macOS or WinGet on Windows. Linux preview installation follows the [official manual instructions](https://learn.chatgpt.com/docs/linux/linux-app). Existing `chatup codex` still installs/configures the Codex CLI. No automatic launch, login or upgrade of existing installations. See the [full contract](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/#chatgpt-desktop).

`chatup codex` and `chatup hermes` default to `gpt-5.6-terra` only when no model is configured; explicit choices and existing configuration retain precedence.

## Current Capabilities

| Capability group | Commands |
| --- | --- |
| Base runtime | `doctor`, `uv`, `nodejs`, `docker`, `zsh`, `chrome-for-testing`, `chromedriver`, `playwright`, `frp` |
| Workspace scaffold | `workspace` |
| Desktop apps | `macos` (Snipaste/iTerm2/Chrome/Blender selection), `chrome`, `iterm` (macOS only), `chatgpt` (includes Codex) |
| Video projects | `remotion` |
| Local service installers | `gitea`, `mysql`, `nginx`, `crs` |
| Agent toolchains | `cc-connect`, `claude`, `codex`, `cursor-agent`, `opencode`, `hermes`, `lark-cli` |

Desktop apps use native application paths; ChatArch-managed install targets stay under `~/.chatarch/...`, for example `~/.chatarch/chrome-for-testing`, `~/.chatarch/chromedriver`, `~/.chatarch/playwright`, `~/.chatarch/chattea`, `~/.chatarch/discourse`, `~/.chatarch/zulip`, `~/.chatarch/chatdata`, `~/.chatarch/nginx`, and `~/.chatarch/crs/local`. `cursor-agent`, `discourse`, and `zulip` register typed ChatEnv profiles; an explicitly selected profile is isolated from credentials in the process environment. ChatStyle renders the CLI tree from the registered command surface. See `docs/capability-map.en.md` for the full capability boundary.

## Development

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
chatup --version
chatup --tree
chatup --tree-brief
```

See the documentation site's [Quick Start](https://arch.gh.wzhecnu.cn/ChatUp/en/quickstart/), [Command Reference](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/), and [CLI Capability Map](https://arch.gh.wzhecnu.cn/ChatUp/en/capability-map/) for more details.

## Release

Release is tag-driven. A `vX.Y.Z` tag must match `src/chatup/__init__.py::__version__`; the publish workflow builds and publishes to PyPI through Trusted Publishing/OIDC.
