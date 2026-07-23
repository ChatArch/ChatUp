# ChatUp

ChatUp is the standalone ChatArch setup CLI. It carries the former `chattool setup` responsibilities as first-level commands for development runtimes, agent CLIs, workspace scaffolds, and local services. For example, `chattool setup workspace` maps to `chatup workspace`.

- Documentation: <https://arch.gh.wzhecnu.cn/ChatUp/en/>
- Chinese README: [README.md](README.md)
- Source: <https://github.com/ChatArch/ChatUp>

## Quick Start

```bash
chatup --help
chatup doctor
chatup uv
chatup workspace default ~/Playground
```

Common install commands:

```bash
chatup gitea --install-dir ~/.chatarch/bin --force
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## Current Capabilities

- `chatup uv`: installs `uv` and creates the ChatArch Python runtime. Defaults are `~/.chatarch/venv` and Python 3.12.
- `chatup workspace`: initializes the human-AI collaboration workspace scaffold with `AGENTS.md`, `projects/`, `archive/`, `core/`, `skills/`, and `public/`.
- `chatup gitea`: installs the ChatArch-maintained Gitea binary from GitHub Release assets in `ChatArch/gitea`.
- `chatup crs`: installs the canonical `@chatarch/claude-relay-service` npm package, prepares a local Redis component, writes local config and secret files, builds the admin SPA, starts CRS, and runs a local smoke check.
- `chatup cc-connect`, `chatup claude`, `chatup codex`, `chatup opencode`, `chatup hermes`, and `chatup lark-cli`: configure common ChatArch agent, model, and Feishu/Lark toolchains.
- `chatup nodejs`, `chatup docker`, `chatup zsh`, `chatup chrome`, and `chatup frp`: prepare common system runtimes.

## Development

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
```

See the documentation site's [Quick Start](https://arch.gh.wzhecnu.cn/ChatUp/en/quickstart/) and [Command Reference](https://arch.gh.wzhecnu.cn/ChatUp/en/commands/) for more details.

## Release

Release is tag-driven. A `vX.Y.Z` tag must match `src/chatup/__init__.py::__version__`; the publish workflow builds and publishes to PyPI through Trusted Publishing/OIDC.
