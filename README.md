# ChatUp

ChatUp 是 ChatArch 的独立环境与工具安装 CLI。它承接原来 `chattool setup` 的职责，把常用开发环境、Agent CLI、工作区脚手架和本地服务安装整理成一级命令，例如 `chattool setup workspace` 对应 `chatup workspace`。

- 文档站：<https://arch.gh.wzhecnu.cn/ChatUp/>
- English README: [README.en.md](README.en.md)
- Source: <https://github.com/ChatArch/ChatUp>

## 快速开始

```bash
chatup --help
chatup doctor
chatup uv
chatup workspace default ~/Playground
```

常见安装命令：

```bash
chatup gitea --force
chatup mysql
chatup nginx
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## 当前能力

- `chatup uv`：安装 `uv`，并创建 ChatArch Python 运行环境。默认目标是 `~/.chatarch/venv`，默认 Python 版本是 3.12。
- `chatup workspace`：初始化人类-AI 协作工作区，包括 `AGENTS.md`、`projects/`、`archive/`、`core/`、`skills/`、`public/` 等约定目录。
- `chatup gitea`：从 `ChatArch/gitea` GitHub Release 安装 ChatArch 维护的 Gitea；默认使用 latest，可选生成 ChatTea-compatible `app.ini` 和 user-level systemd service。
- `chatup mysql`：安装并准备 ChatData-compatible user-level MySQL runtime、实例目录、`my.cnf` 和可选 user-level systemd service。
- `chatup nginx`：准备 `~/.chatarch/nginx` 下的 user-level NGINX runtime/config/log/run/temp 布局，也可生成 NGINX reverse-proxy、HTTPS proxy、WebSocket proxy、static root 和 redirect 配置模板。
- `chatup crs`：安装 canonical `@chatarch/claude-relay-service` npm 包，准备本地 Redis 组件，生成本地配置和 secret 文件，构建 admin SPA，启动 CRS，并执行本地 smoke check。
- `chatup cc-connect`、`chatup claude`、`chatup codex`、`chatup opencode`、`chatup hermes`、`chatup lark-cli`：配置 ChatArch 常用 Agent、模型与飞书工具链。
- `chatup nodejs`、`chatup docker`、`chatup zsh`、`chatup chrome`、`chatup frp`：准备常用系统运行环境。

## 开发

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
```

更多使用说明见文档站的 [快速开始](https://arch.gh.wzhecnu.cn/ChatUp/quickstart/) 和 [命令参考](https://arch.gh.wzhecnu.cn/ChatUp/commands/)。

## 发布

发布由 tag 驱动。`vX.Y.Z` tag 必须与 `src/chatup/__init__.py::__version__` 一致；发布 workflow 会通过 PyPI Trusted Publishing/OIDC 构建并发布到 PyPI。
