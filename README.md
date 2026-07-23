# ChatUp

ChatUp 是 ChatArch 的独立环境与工具安装 CLI。它承接原来 `chattool setup` 的职责，把常用开发环境、Agent CLI、工作区脚手架和本地服务安装整理成一级命令，例如 `chattool setup workspace` 对应 `chatup workspace`。

- 文档站：<https://arch.gh.wzhecnu.cn/ChatUp/>
- English README: [README.en.md](README.en.md)
- Source: <https://github.com/ChatArch/ChatUp>

按场景选择文档：

| 场景 | 文档 |
| --- | --- |
| 从空机器验证 ChatUp、Python runtime 和 workspace | `docs/quickstart.md` |
| 查看完整 CLI 树、命令分组、参数边界和服务默认路径 | `docs/commands.md` |
| 校对哪些 ChatArch setup 流程已经有一等命令 | `docs/capability-map.md` |
| 理解 `chatup workspace` 创建的目录和项目记录约定 | `docs/workspace.md` |
| 安装 ChatTea-compatible Gitea、ChatData-compatible MySQL、user-level NGINX 和 CRS | `docs/commands.md` |

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

| 能力组 | 命令 |
| --- | --- |
| 基础运行环境 | `doctor`、`uv`、`nodejs`、`docker`、`zsh`、`chrome`、`frp` |
| 工作区脚手架 | `workspace` |
| 本地服务安装 | `gitea`、`mysql`、`nginx`、`crs` |
| Agent 工具链 | `cc-connect`、`claude`、`codex`、`opencode`、`hermes`、`lark-cli` |

所有新增服务类默认目录都收敛到 `~/.chatarch/...`，例如 `~/.chatarch/chattea`、`~/.chatarch/chatdata`、`~/.chatarch/nginx` 和 `~/.chatarch/crs/local`。更完整的能力边界见 `docs/capability-map.md`。

## 开发

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
```

更多使用说明见文档站的 [快速开始](https://arch.gh.wzhecnu.cn/ChatUp/quickstart/)、[命令参考](https://arch.gh.wzhecnu.cn/ChatUp/commands/) 和 [CLI 能力地图](https://arch.gh.wzhecnu.cn/ChatUp/capability-map/)。

## 发布

发布由 tag 驱动。`vX.Y.Z` tag 必须与 `src/chatup/__init__.py::__version__` 一致；发布 workflow 会通过 PyPI Trusted Publishing/OIDC 构建并发布到 PyPI。
