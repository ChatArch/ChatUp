# ChatUp CLI 能力地图

这篇文档是当前 ChatUp CLI 的简明能力地图，用来校对哪些机器初始化、本地服务和 Agent 工具链流程已经有一等命令，哪些边界仍应交给对应项目或系统运维层。

更完整的参数、默认路径和命令约定见 [命令参考](commands.md)。从空机器开始的操作路径见 [快速开始](quickstart.md)。

## 顶层命令

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

## 能力分组

<div class="grid cards" markdown>

- **基础运行环境**

    `uv`、`nodejs`、`docker`、`zsh`、`chrome`、`frp` 面向一台新机器的基础依赖准备。`doctor` 用来做最小健康检查。

- **本地服务安装**

    `gitea`、`mysql`、`nginx`、`crs` 负责 ChatArch 常用本地服务的 user-level 安装和初始化，默认路径收敛到 `~/.chatarch/...`。

- **Agent 工具链**

    `claude`、`codex`、`opencode`、`hermes`、`cc-connect`、`lark-cli` 负责模型 CLI、Agent runtime 和飞书工具链配置。

- **工作区脚手架**

    `workspace` 负责创建 `AGENTS.md`、`projects/`、`core/`、`skills/`、`public/` 等 ChatArch workspace 约定目录。

</div>

## 基础运行环境

```text
chatup doctor              # 检查 CLI 当前是否可调用
chatup uv                  # 安装/复用 uv，创建 ~/.chatarch/venv
chatup nodejs              # 安装 nvm 和默认 LTS Node.js
chatup docker              # 检查 Docker daemon 和当前用户权限
chatup zsh                 # 配置 zsh / oh-my-zsh / 插件 / alias
chatup chrome              # 安装 Chrome 和 Chromedriver
chatup frp                 # 安装 FRP Client/Server
```

这些命令只承诺把 ChatArch 常用基础依赖准备好；它们不是通用系统包管理器，也不替代发行版的软件源策略。

## 本地服务安装

```text
chatup gitea               # 对齐 ChatTea 的 Gitea binary/work path/config/service
chatup mysql               # 对齐 ChatData 的 MySQL runtime/instance/service
chatup nginx               # 准备 ~/.chatarch/nginx runtime/config/log/run/temp
chatup crs                 # 准备本地 CRS、Redis、secret、admin SPA 和 smoke check
```

本地服务命令默认使用 user-level 布局：

| 命令 | 默认目录 | 运行边界 |
| --- | --- | --- |
| `chatup gitea` | `~/.chatarch/chattea` | Gitea 默认监听 `127.0.0.1:3000`，公网入口交给 NGINX/public-entry。 |
| `chatup mysql` | `~/.chatarch/chatdata` | MySQL 默认监听 `127.0.0.1:3307`，可创建 user-level service。 |
| `chatup nginx` | `~/.chatarch/nginx` | 不写 `/etc/nginx`，不重载系统服务；可生成入口模板。 |
| `chatup crs` | `~/.chatarch/crs/local` | 本地 CRS + Redis + smoke check；secret 文件权限受限。 |

## Agent 工具链

```text
chatup claude              # 配置 Claude Code CLI 和配置文件
chatup codex               # 配置 Codex CLI 和配置文件
chatup opencode            # 配置 OpenCode CLI 和配置文件
chatup hermes              # 安装 Hermes Agent 和可选 WebUI
chatup cc-connect          # 安装 CC Connect CLI 和运行依赖
chatup lark-cli            # 配置官方 lark-cli，并复用 ChatEnv 飞书配置
```

这些命令负责本机 CLI 与配置文件准备；具体模型供应商账号、token、工作流权限和平台策略仍由对应工具自身或 ChatEnv 管理。

## 工作区

```text
chatup workspace default ~/Playground  # 初始化 ChatArch workspace
```

`workspace` 只创建和同步目录/规范，不替代项目本身的 repo 初始化、任务 PRD、progress 记录和 review 流程。工作区规范见 [工作区脚手架](workspace.md)。

## 当前不负责的边界

- 不做系统级服务编排；默认不写 `/etc`、不修改系统 NGINX、不创建 root-level service。
- 不作为通用包管理器；只收敛 ChatArch 常用环境和工具链。
- 不打印 secret、token、连接串或 Authorization header。
- 不把计划中的命令写进正式 CLI 树；未来能力应先放在 roadmap 或 PRD，再在实现后进入命令参考。
