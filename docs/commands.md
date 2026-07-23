# 命令参考

本页只列当前已经实现的 `chatup` 一级命令。运行时以 `chatup <command> --help` 为准。

## CLI 树

ChatUp 当前采用一级命令结构，没有 `chatup setup ...` 子树。所有安装、初始化和配置能力都直接挂在 `chatup` 下：

```text
chatup
|-- doctor      # 检查 ChatUp 是否可调用
|-- uv          # 安装 uv，并创建默认 ChatArch Python 运行环境
|-- workspace   # 初始化 ChatArch workspace scaffold
|-- nodejs      # 安装 nvm 和默认 LTS Node.js
|-- docker      # 检查 Docker 环境，并提示 sudo 配置
|-- zsh         # 配置 zsh / oh-my-zsh / 插件 / alias
|-- chrome      # 安装 Chrome 和 Chromedriver
|-- frp         # 安装 FRP Client/Server
|-- gitea       # 安装 ChatTea-compatible Gitea runtime/config/service
|-- mysql       # 安装 ChatData-compatible MySQL runtime/instance/service
|-- nginx       # 准备 user-level NGINX runtime，并生成入口模板
|-- crs         # 安装本地 Claude Relay Service + Redis + smoke check
|-- cc-connect  # 安装 CC Connect CLI 和运行依赖
|-- claude      # 配置 Claude Code CLI 和配置文件
|-- codex       # 配置 Codex CLI 和配置文件
|-- opencode    # 配置 OpenCode CLI 和配置文件
|-- hermes      # 安装 Hermes Agent 和可选 WebUI
`-- lark-cli    # 配置官方 lark-cli，并复用 ChatEnv 飞书配置
```

## 命令分组速览

<div class="grid cards" markdown>

- **基础环境**

    `doctor`、`uv`、`nodejs`、`docker`、`zsh`、`chrome`、`frp` 负责机器级运行环境准备和检查。

- **本地服务**

    `gitea`、`mysql`、`nginx`、`crs` 负责 ChatArch 常用本地服务，默认落在 `~/.chatarch/...`。

- **Agent 工具链**

    `claude`、`codex`、`opencode`、`hermes`、`cc-connect`、`lark-cli` 负责模型、Agent 和飞书工具链配置。

- **工作区**

    `workspace` 创建 ChatArch 人类-AI 协作目录结构和项目记录入口。

</div>

## 基础命令

| 命令 | 当前能力 |
|---|---|
| `chatup doctor` | 检查 ChatUp 是否可调用。 |
| `chatup uv` | 安装 `uv` 并创建 ChatArch Python 运行环境。 |
| `chatup nodejs` | 安装 nvm 和默认 LTS Node.js。 |
| `chatup docker` | 检查 Docker 环境，并在需要时给出 sudo 相关建议。 |
| `chatup zsh` | 配置 zsh、oh-my-zsh、插件、主题和 shell alias。 |
| `chatup chrome` | 安装 Chrome 与 Chromedriver。 |
| `chatup frp` | 安装 FRP Client/Server。 |

## Agent 与工具链

| 命令 | 当前能力 |
|---|---|
| `chatup claude` | 配置 Claude Code CLI 和配置文件。 |
| `chatup codex` | 配置 Codex CLI 和配置文件。 |
| `chatup opencode` | 配置 OpenCode CLI 和配置文件。 |
| `chatup hermes` | 安装 Hermes Agent 和可选 Hermes WebUI。 |
| `chatup cc-connect` | 安装 CC Connect CLI 和运行依赖。 |
| `chatup lark-cli` | 配置官方 lark-cli，并复用 ChatEnv 飞书配置。 |

## 本地服务

| 命令 | 当前能力 |
|---|---|
| `chatup gitea` | 从 `ChatArch/gitea` Release assets 安装 ChatArch Gitea；默认跟随 latest，可选生成 ChatTea-compatible `app.ini` 和 user-level systemd service。 |
| `chatup mysql` | 安装并准备 ChatData-compatible user-level MySQL runtime、实例目录、`my.cnf` 和可选 user-level systemd service。 |
| `chatup nginx` | 准备 `~/.chatarch/nginx` 下的 user-level NGINX runtime/config/log/run/temp 布局，也可生成 reverse-proxy、HTTPS proxy、WebSocket proxy、static root 和 redirect 模板。 |
| `chatup crs` | 安装本地 Claude Relay Service，准备 Redis、配置、secret、admin SPA 和 smoke check。 |

## 工作区

| 命令 | 当前能力 |
|---|---|
| `chatup workspace` | 初始化 ChatArch 人类-AI 协作 workspace。 |

## Gitea 命令约定

`chatup gitea` 对齐 ChatTea 的本地 Gitea 布局：

- 默认 release：`latest`，从 `ChatArch/gitea` 最新 GitHub Release 解析。
- 默认 binary：`~/.chatarch/chattea/bin/gitea`。
- 默认 work path：`~/.chatarch/chattea/gitea`。
- 可选 `--init` 会生成 `custom/conf/app.ini`，权限为 `0600`。
- 可选 `--service` 会写入 user-level systemd service。
- Gitea 默认监听 `127.0.0.1:3000`，公网或本地域名入口交给 NGINX/public-entry 层。

常用形式：

```bash
chatup gitea --force
chatup gitea --init --service --base-url http://127.0.0.1:3000
chatup gitea --init --database-backend mysql --database-host ~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
```

## MySQL 命令约定

`chatup mysql` 复用 ChatData 第一版 no-sudo runtime 模型：

- 默认 MySQL 版本：`8.4.6`。
- 默认 home：`~/.chatarch/chatdata`。
- 默认实例：`default`。
- 默认端口：`3307`。
- 默认绑定：`127.0.0.1`。
- 默认会下载 runtime、初始化实例目录、生成 `my.cnf` 并写入 user-level systemd service，但不会启动服务。
- `--smoke` 和 `--database` 需要 `--start`，避免在未启动服务时延迟失败。

常用形式：

```bash
chatup mysql
chatup mysql --start --smoke
chatup mysql --start --database gitea
chatup mysql --home ~/.chatarch/chatdata --name default --port 3307
```

## NGINX 命令约定

`chatup nginx` 默认准备 user-level NGINX，而不是修改系统 NGINX：

- 默认 home：`~/.chatarch/nginx`。
- 默认 binary：复制已有 `nginx` 到 `~/.chatarch/nginx/bin/nginx`；如系统 PATH 中没有 `nginx`，可用 `--binary PATH` 指定已有二进制。
- 默认 config：`~/.chatarch/nginx/conf/nginx.conf`。
- 默认 logs/run/temp：`~/.chatarch/nginx/logs`、`~/.chatarch/nginx/run`、`~/.chatarch/nginx/temp`。
- 默认站点目录：`~/.chatarch/nginx/conf/sites-available` 和 `~/.chatarch/nginx/conf/sites-enabled`。
- 默认监听：`127.0.0.1:8080`。
- 默认写入 user-level systemd service；不会写 `/etc/nginx`，不会重载系统服务。

```bash
chatup nginx
chatup nginx --home ~/.chatarch/nginx --binary /usr/sbin/nginx --port 8080
chatup nginx --start --smoke
```

`chatup nginx` 也保留模板生成模式：

```bash
chatup nginx --list
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup nginx websocket-proxy ./ws.conf --set SERVER_NAME=ws.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup nginx static-root ./site.conf --set SERVER_NAME=site.local.example.invalid --set ROOT_DIR=/srv/site
```

## CRS 命令约定

`chatup crs` 的默认目标是本地开发环境：

- 默认安装目录：`~/.chatarch/crs/local`
- 默认 CRS 端口：`12392`
- 默认 Redis 端口：`6379`
- secret 文件：写入安装目录下的 `.local-secrets.env`，并使用受限权限。
- 默认会启动服务并运行 smoke check。

常用形式：

```bash
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
chatup crs --no-start --no-smoke
```
