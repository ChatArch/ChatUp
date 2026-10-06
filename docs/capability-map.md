# ChatUp CLI 能力地图

这篇文档是当前 ChatUp CLI 的简明能力地图，用来校对哪些机器初始化、本地服务和 Agent 工具链流程已经有一等命令，哪些边界仍应交给对应项目或系统运维层。

更完整的参数、默认路径和命令约定见 [命令参考](commands.md)。从空机器开始的操作路径见 [快速开始](quickstart.md)。

## 顶层命令

```text
chatup
|-- doctor      # 检查 ChatUp 是否可调用
|-- uv          # 安装 uv，并创建默认 ChatArch Python 运行环境
|-- workspace   # 初始化 ChatArch workspace scaffold
|-- nodejs      # 安装默认 LTS Node.js（POSIX 用 nvm，Windows 用 ChatArch 便携 ZIP）
|-- docker      # 检查 Docker 环境，并提示 sudo 配置
|-- zsh         # 配置 zsh / oh-my-zsh / 插件 / alias
|-- chrome              # 按当前系统安装普通 Google Chrome
|-- snipaste            # 在 macOS 或 Windows 安装 Snipaste
|-- iterm               # 安装 iTerm2（仅限 macOS）
|-- macos               # 勾选 macOS 应用，Apple Silicon 可选 Blender
|-- remotion            # 初始化带锁定依赖的本地视频项目
|-- chrome-for-testing # 管理 Google Chrome for Testing 浏览器
|-- chromedriver       # 管理 ChromeDriver WebDriver server
|-- playwright         # 管理 Playwright package 与 Chromium browser
|-- frp         # 安装 FRP Client/Server
|-- gitea       # 安装 ChatTea-compatible Gitea runtime/config/service
|-- glance      # 安装已校验的 ChatArch Glance loopback runtime
|-- discourse   # 准备 Discourse docker 配置和 ChatEnv 管理的管理员凭据
|-- zulip       # 准备 Zulip Docker Compose 配置和 ChatEnv 管理的管理员凭据
|-- mysql       # 安装 ChatData-compatible MySQL runtime/instance/service
|-- nginx       # 准备 user-level NGINX runtime，并生成入口模板
|-- crs         # 安装本地 Claude Relay Service + Redis + smoke check
|-- cc-connect  # 安装 CC Connect CLI 和运行依赖
|-- claude      # 配置 Claude Code CLI 和配置文件
|-- chatgpt      # 安装新版 ChatGPT 桌面应用（含 Codex）
|-- codex       # 配置 Codex CLI 和配置文件（设置时使用 CODEX_HOME）
|-- opencode    # 配置 OpenCode CLI 和配置文件
|-- hermes      # 安装 Hermes Agent 和可选 WebUI
`-- lark-cli    # 配置官方 lark-cli，并复用 ChatEnv 飞书配置
```

## 能力分组

<div class="grid cards" markdown>

- **基础运行环境**

    `uv`、`nodejs`、`docker`、`zsh`、`chrome-for-testing`、`chromedriver`、`playwright`、`frp` 面向一台新机器的基础依赖准备。`doctor` 用来做最小健康检查。

- **本地服务安装**

    `gitea`、`glance`、`discourse`、`zulip`、`mysql`、`nginx`、`crs` 负责 ChatArch 常用本地服务的 user-level/ChatArch-contained 安装和初始化，默认路径收敛到 `~/.chatarch/...`。Discourse/Zulip 的管理员凭据由 ChatEnv profile 或 env 文件提供。

- **Agent 工具链**

    `claude`、`codex`、`opencode`、`hermes`、`cc-connect`、`lark-cli` 负责模型 CLI、Agent runtime 和飞书工具链配置。

- **工作区脚手架**

    `workspace` 负责创建 `AGENTS.md`、`projects/`、`core/`、`skills/`、`public/` 等 ChatArch workspace 约定目录。

</div>

## 基础运行环境

```text
chatup doctor              # 检查 CLI 当前是否可调用
chatup uv                  # 安装/复用 uv，创建 ~/.chatarch/venv
chatup nodejs              # 安装默认 LTS Node.js（POSIX 用 nvm，Windows 用 ChatArch 便携 ZIP）
chatup docker              # 检查 Docker daemon 和当前用户权限
chatup zsh                 # 配置 zsh / oh-my-zsh / 插件 / alias
chatup chrome-for-testing  # 管理 versioned Google Chrome for Testing 浏览器
chatup chromedriver        # 管理 ChromeDriver WebDriver server
chatup playwright          # 管理 Playwright package 与 Chromium browser
chatup frp                 # 安装 FRP Client/Server
```

这些命令只承诺把 ChatArch 常用基础依赖准备好；它们不是通用系统包管理器，也不替代发行版的软件源策略。Windows 上，`chatup nodejs` 优先回读当前 PATH 中合格的 Node/npm；否则会把经 Node.js 官方 SHA-256 清单校验的便携 LTS ZIP 安装到 `$CHATARCH_HOME/nodejs`，并通过检测到的 `node.exe` 与 `npm-cli.js` 的 argv 列表运行 npm。由该受管 runtime 全局安装的 npm 包放在 `$CHATARCH_HOME/nodejs/npm`，不会写入系统 npm prefix 或系统 PATH。`chatup chrome-for-testing` 提供机器可读浏览器 descriptor，供 ChatPost 等扩展/CDP 消费方复用；`chatup chromedriver` 为 WebDriver 消费方独立提供 driver descriptor。`chatup playwright` 则固定 Playwright package、browser revision/version 和 executable path。Profile、账号和 Cookie 始终由消费方管理。

## 本地服务安装

```text
chatup gitea               # 对齐 ChatTea 的 Gitea binary/work path/config/service
chatup glance              # 校验并初始化 loopback Glance runtime，不启动服务
chatup discourse           # 准备 Discourse app.yml、shared 数据目录和 ChatEnv 管理的 admin.env
chatup zulip               # 准备 Zulip Compose、bind-mount 数据目录和 ChatEnv 管理的 admin.env
chatup mysql               # 对齐 ChatData 的 MySQL runtime/instance/service
chatup nginx               # 准备 ~/.chatarch/nginx runtime/config/log/run/temp
chatup crs                 # 准备本地 CRS、Redis、secret、admin SPA 和 smoke check
```

本地服务命令默认使用 user-level 布局：

| 命令 | 默认目录 | 运行边界 |
| --- | --- | --- |
| `chatup gitea` | `~/.chatarch/chattea` | Gitea 默认监听 `127.0.0.1:3000`，公网入口交给 NGINX/public-entry。 |
| `chatup glance` | `~/.chatarch/glance` | 仅安装已校验的维护版并保留运行数据；启动、升级和公网入口均为显式运维操作。 |
| `chatup discourse` | `~/.chatarch/discourse` | 生成 Discourse Docker app.yml 和 admin env；默认不改系统 NGINX，不打印密码。 |
| `chatup zulip` | `~/.chatarch/zulip` | 生成 Zulip Compose/bind mounts/secrets；默认不启动，`--start` 才执行 Compose。 |
| `chatup mysql` | `~/.chatarch/chatdata` | MySQL 默认监听 `127.0.0.1:3307`，可创建 user-level service。 |
| `chatup nginx` | `~/.chatarch/nginx` | 不写 `/etc/nginx`，不重载系统服务；可生成入口模板。 |
| `chatup crs` | `~/.chatarch/crs/local` | 本地 CRS + Redis + smoke check；secret 文件权限受限。 |

## 桌面应用

`chatup macos` 默认勾选所有支持的应用：Apple Silicon 提供 Snipaste、iTerm2、Chrome、Blender，Intel 提供前三项。支持 `--app` 子集、`-I` 非交互和 `--dry-run` 预览；使用官方安装包并验证签名，Blender 另校验固定版本的 SHA-256 与公证，无需 Homebrew。详见[macOS 安装入口](commands.md#macos)。

`chatup remotion PROJECT_DIR` 创建带锁定依赖和可渲染示例的视频项目，要求已有 Node/npm，保护已有目录并检测本机浏览器。它使用项目目录，可配合 macOS 的 Chrome/Blender 安装入口。详见[Remotion 约定](commands.md#remotion)。

`chatup chrome` 按系统安装普通 Google Chrome；`chatup snipaste` 在 macOS 或 Windows 安装 Snipaste；`chatup iterm` 在 macOS 安装 iTerm2。三个命令支持 `--dry-run`，验证并复用已有安装，macOS 无需 Homebrew。Windows 通过 WinGet 的精确包 ID 验证。详见[安装约定](commands.md#chrome-iterm)。

`chatup chatgpt` 通过 macOS Homebrew 或 Windows 官方 Microsoft Store 精确 ID 安装含 Codex 的新版 ChatGPT 桌面应用。`--dry-run` 无副作用，安装后回读包管理器记录。应用与缓存使用包管理器/OpenAI 的原生目录，不属于 ChatArch 自管状态。不启动应用、不登录、不改 Codex CLI 配置，也不自动安装 Linux preview。详见[桌面安装约定](commands.md#chatgpt-desktop)。

## Agent 工具链

```text
chatup claude              # 配置 Claude Code CLI 和配置文件
chatup codex               # 配置 Codex CLI 和配置文件（设置时使用 CODEX_HOME）
chatup opencode            # 配置 OpenCode CLI 和配置文件
chatup hermes              # 安装 Hermes Agent 和可选 WebUI
chatup cc-connect          # 安装 CC Connect CLI 和运行依赖
chatup lark-cli            # 配置官方 lark-cli，并复用 ChatEnv 飞书配置
```

这些命令负责本机 CLI 与配置文件准备；具体模型供应商账号、token、工作流权限和平台策略仍由对应工具自身或 ChatEnv 管理。

## 工作区

```text
chatup workspace ~/Playground  # 初始化 ChatArch workspace
```

`workspace` 只创建和同步目录/规范，不替代项目本身的 repo 初始化、任务 PRD、progress 记录和 review 流程。工作区规范见 [工作区脚手架](workspace.md)。

## 当前不负责的边界

- 不做系统级服务编排；默认不写 `/etc`、不修改系统 NGINX、不创建 root-level service。
- 不作为通用包管理器；只收敛 ChatArch 常用环境和工具链。
- 不打印 secret、token、连接串或 Authorization header。
- 不把计划中的命令写进正式 CLI 树；未来能力应先放在 roadmap 或 PRD，再在实现后进入命令参考。
