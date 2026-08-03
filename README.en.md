# ChatUp

ChatUp is the standalone ChatArch setup CLI. It carries the former `chattool setup` responsibilities as first-level commands for development runtimes, agent CLIs, workspace scaffolds, and local services. For example, `chattool setup workspace` maps to `chatup workspace`.

- Documentation: <https://arch.gh.wzhecnu.cn/ChatUp/en/>
- Chinese README: [README.md](README.md)
- Source: <https://github.com/ChatArch/ChatUp>

Choose documentation by scenario:

| Scenario | Document |
| --- | --- |
| Verify ChatUp, the Python runtime, and a workspace on a new machine | `docs/quickstart.en.md` |
| Read the complete top-level CLI tree and Chrome install/Python contract | `docs/cli-tree.en.md` |
| Read command groups, option boundaries, and service defaults | `docs/commands.en.md` |
| Check which ChatArch setup flows have first-class commands | `docs/capability-map.en.md` |
| Understand the directories and project-record conventions created by `chatup workspace` | `docs/workspace.en.md` |
| Install ChatTea-compatible Gitea, ChatData-compatible MySQL, user-level NGINX, and CRS | `docs/commands.en.md` |

## Quick Start

```bash
chatup --help
chatup doctor
chatup uv
chatup chrome
chatup workspace default ~/Playground
```

Common install commands:

```bash
chatup gitea --force
chatup mysql
chatup nginx
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## Current Capabilities

| Capability group | Commands |
| --- | --- |
| Base runtime | `doctor`, `uv`, `nodejs`, `docker`, `zsh`, `chrome`, `frp` |
| Workspace scaffold | `workspace` |
| Local service installers | `gitea`, `mysql`, `nginx`, `crs` |
| Agent toolchains | `cc-connect`, `claude`, `codex`, `opencode`, `hermes`, `lark-cli` |

New install targets stay under `~/.chatarch/...`, for example `~/.chatarch/chrome`, `~/.chatarch/chattea`, `~/.chatarch/chatdata`, `~/.chatarch/nginx`, and `~/.chatarch/crs/local`. See `docs/capability-map.en.md` for the full capability boundary.

## Development

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
```

See the documentation site's [Quick Start](https://arch.gh.wzhecnu.cn/ChatUp/en/quickstart/), [Command Reference](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/), and [CLI Capability Map](https://arch.gh.wzhecnu.cn/ChatUp/en/capability-map/) for more details.

## Release

Release is tag-driven. A `vX.Y.Z` tag must match `src/chatup/__init__.py::__version__`; the publish workflow builds and publishes to PyPI through Trusted Publishing/OIDC.
