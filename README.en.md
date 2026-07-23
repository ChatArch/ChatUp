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
chatup gitea --force
chatup mysql
chatup nginx
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## Current Capabilities

- `chatup uv`: installs `uv` and creates the ChatArch Python runtime. Defaults are `~/.chatarch/venv` and Python 3.12.
- `chatup workspace`: initializes the human-AI collaboration workspace scaffold with `AGENTS.md`, `projects/`, `archive/`, `core/`, `skills/`, and `public/`.
- `chatup gitea`: installs the ChatArch-maintained Gitea from GitHub Release assets in `ChatArch/gitea`; defaults to latest and can write a ChatTea-compatible `app.ini` plus user-level systemd service.
- `chatup mysql`: installs and prepares a ChatData-compatible user-level MySQL runtime, instance layout, `my.cnf`, and optional user-level systemd service.
- `chatup nginx`: prepares a user-level NGINX runtime/config/log/run/temp layout under `~/.chatarch/nginx`, and can also generate NGINX reverse-proxy, HTTPS proxy, WebSocket proxy, static root, and redirect config templates.
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
