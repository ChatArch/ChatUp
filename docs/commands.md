# 命令参考

本页只列当前已经实现的 `chatup` 一级命令。运行时以 `chatup <command> --help` 为准。

## CLI 树

ChatUp 当前采用一级命令结构，没有 `chatup setup ...` 子树。所有安装、初始化和配置能力都直接挂在 `chatup` 下：

```text
chatup
|-- doctor      # 检查 ChatUp 是否可调用
|-- uv          # 安装 uv，并创建默认 ChatArch Python 运行环境
|-- workspace   # 初始化 ChatArch workspace scaffold
|-- nodejs      # 安装默认 LTS Node.js（POSIX 使用 nvm，Windows 使用 ChatArch 便携 ZIP）
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
|-- glance      # 安装已校验的 ChatArch Glance loopback runtime（不启动）
|-- discourse   # 准备 Discourse docker 配置和 ChatEnv 管理的管理员凭据
|-- zulip       # 准备 Zulip Docker Compose 配置和 ChatEnv 管理的管理员凭据
|-- mysql       # 安装 ChatData-compatible MySQL runtime/instance/service
|-- twikoo      # 安装多实例 Twikoo 评论服务 runtime/instance/service
|-- nginx       # 准备 user-level NGINX runtime，并生成入口模板
|-- crs         # 安装本地 Claude Relay Service + Redis + smoke check
|-- cc-connect  # 安装 CC Connect CLI 和运行依赖
|-- claude      # 配置 Claude Code CLI 和配置文件
|-- chatgpt      # 安装新版 ChatGPT 桌面应用（含 Codex）
|-- codex       # 配置 Codex CLI 和配置文件（设置时使用 CODEX_HOME）
|-- cursor-agent # 配置 Cursor Agent CLI 登录态和配置文件
|-- opencode    # 配置 OpenCode CLI 和配置文件
|-- hermes      # 安装 Hermes Agent 和可选 WebUI
`-- lark-cli    # 配置官方 lark-cli，并复用 ChatEnv 飞书配置
```

## 命令分组速览

<div class="grid cards" markdown>

- **基础环境**

    `doctor`、`uv`、`nodejs`、`docker`、`zsh`、`chrome-for-testing`、`chromedriver`、`playwright`、`frp` 负责机器级运行环境准备和检查。

- **本地服务**

    `gitea`、`glance`、`discourse`、`zulip`、`mysql`、`twikoo`、`nginx`、`crs` 负责 ChatArch 常用本地服务，默认落在 `~/.chatarch/...`，其中 Discourse/Zulip 管理员凭据从 ChatEnv 读取。

- **Agent 工具链**

    `claude`、`codex`、`cursor-agent`、`opencode`、`hermes`、`cc-connect`、`lark-cli` 负责模型、Agent 和飞书工具链配置。

- **工作区**

    `workspace` 创建 ChatArch 人类-AI 协作目录结构和项目记录入口。

</div>

## Windows 兼容性

- `chatup uv` 在 Windows 使用官方 PowerShell installer，并输出 `Scripts/Activate.ps1` 激活提示。
- `chatup nodejs` 先在 Windows 的当前 PATH 中回读 `node`/`npm`；缺失或版本不足时，会从 Node.js 官方 LTS release 下载便携 ZIP，并以官方 `SHASUMS256.txt` 的 SHA-256 校验后安全解压到 `$CHATARCH_HOME/nodejs`。它不写 nvm shell init、不改系统 Node/PATH；npm 子进程通过检测到的 `node.exe` 与 `npm-cli.js` 的 argv 列表执行，可保留空格、Unicode 和 shell 元字符路径。由受管 runtime 执行的 npm 全局安装固定在 `$CHATARCH_HOME/nodejs/npm`，并仅对该子进程加入 PATH。
- `chatup docker` 在 Windows 检查 Docker Desktop 提供的 `docker`/`docker compose`，跳过 Unix group 和 systemd 检查。
- `chatup mysql` 会选择 MySQL Windows ZIP asset、`.exe` 二进制名和 TCP client config；`gitea`/`mysql`/`twikoo`/`nginx` 的 `--service` 仍依赖 user-level systemd，在 Windows 会给出明确错误。
- `chatup cursor-agent --credential-store file-wrapper` 在 Windows 写 `.cmd` wrapper；`chatup frp` 支持 Windows ZIP release asset；`zsh` 和 `crs` 仍属于 POSIX/Linux-only setup。

## 基础命令

| 命令 | 当前能力 |
|---|---|
| `chatup doctor` | 检查 ChatUp 是否可调用。 |
| `chatup uv` | 安装 `uv` 并创建 ChatArch Python 运行环境；`--activate / --no-activate` 控制已有 Bash/Zsh 启动配置更新，默认开启。见[快速开始](quickstart.md)。 |
| `chatup nodejs` | POSIX 使用 nvm 安装默认 LTS Node.js；Windows 复用合格 PATH runtime，或在 ChatArch home 内 bootstrap 经官方 SHA-256 校验的便携 LTS ZIP。 |
| `chatup docker` | 检查 Docker 环境，并在需要时给出 sudo 相关建议。 |
| `chatup zsh` | 配置 zsh、oh-my-zsh、插件、主题和 shell alias。 |
| `chatup chrome-for-testing` | 独立管理 Google Chrome for Testing 浏览器及其 JSON/Python descriptor。 |
| `chatup chromedriver` | 独立管理 ChromeDriver WebDriver server，可匹配 CFT 或指定浏览器版本。 |
| `chatup playwright` | 安装精确 Playwright package 与其管理的 Chromium，并输出可复用 descriptor。 |
| `chatup frp` | 安装 FRP Client/Server。 |

## Agent 与工具链

| 命令 | 当前能力 |
|---|---|
| `chatup claude` | 配置 Claude Code CLI 和配置文件。 |
| `chatup codex` | 配置 Codex CLI 和配置文件；设置时使用 `CODEX_HOME`。 |
| `chatup cursor-agent` | 安装/验证 Cursor Agent CLI，并安全复制 `auth.json`、`cli-config.json` 和 `agent-cli-state.json`。 |
| `chatup opencode` | 配置 OpenCode CLI 和配置文件。 |
| `chatup hermes` | 安装 Hermes Agent 和可选 Hermes WebUI；未配置模型时兜底为 `gpt-5.6-terra`，显式模型、profile、已有配置和环境值仍优先。 |
| `chatup cc-connect` | 安装 CC Connect CLI 和运行依赖。 |
| `chatup lark-cli` | 配置官方 lark-cli，并复用 ChatEnv 飞书配置。 |

## macOS 常用应用 {#macos}

`chatup macos` 仅限 macOS。Apple Silicon 提供 Snipaste、iTerm2、Google Chrome、Blender 四个选项，默认全部勾选；Intel 只提供前三项。

```bash
chatup macos
chatup macos --app snipaste
chatup macos --app iterm --app chrome
chatup macos --app blender
chatup macos -I
chatup macos --dry-run
chatup macos -i --dry-run
```

| 参数 / 场景 | 行为 |
| --- | --- |
| 终端中不传 `--app` | 显示默认全选菜单；空格切换、回车确认、Ctrl-C 取消。全部取消勾选后正常退出，不安装。 |
| `--app snipaste\|iterm\|chrome\|blender` | 只安装指定应用；可重复，自动去重，默认不再询问。Blender 仅支持 Apple Silicon。 |
| `-i` | 强制显示菜单，显式 `--app` 作为预选项；没有终端时安装前报错。 |
| `-I`、无终端或 `CHATARCH_AUTO_PROMPT=0` | 不询问；执行显式选择，未指定时安装当前架构支持的全部选项。 |
| `--dry-run` | 默认不询问，只打印所选应用的来源和安装路径；可配合 `-i` 先勾选。不联网、不执行安装、不写目录。 |
| `--log-level DEBUG\|INFO\|WARNING\|ERROR` | 设置安装日志级别，默认 `INFO`。 |

Snipaste 从[官方网站](https://www.snipaste.com/)提供的 [macOS 下载地址](https://dl.snipaste.com/mac)获取 DMG。应用均复用[原生 macOS 安装流程](#chrome-iterm)，无需 Homebrew，校验应用身份与官方签名后安装到 `/Applications`，不可写时使用 `~/Applications`。已有应用验证后复用；不自动升级或启动应用。Snipaste 首次截图所需的系统权限由用户在 macOS 中授权。

Blender 固定使用[官方 5.2.2 LTS Apple Silicon DMG](https://download.blender.org/release/Blender5.2/blender-5.2.2-macos-arm64.dmg)，对照[官方 SHA-256](https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256)校验后才挂载，再检查版本、开发者签名和 Gatekeeper 公证。已有 Blender 验证后保留，不覆盖或降级。Intel Mac 上显式选择 Blender 会在安装任何选项前报错；此版本未实现 Intel 安装。

按选择顺序逐个安装；遇到错误立即停止，已完成的安装保留，再次运行会验证并复用。非 macOS 系统在任何安装前报错，即使只选择 Chrome。

## Remotion 视频项目 {#remotion}

`chatup remotion PROJECT_DIR` 创建 Remotion 4.0.530 / React 19.1.0 项目，附带可渲染的 3 秒 720p 示例和完整 npm 锁文件。需要已有 Node.js >=18.12、npm >=9；安装前检查，不替换系统运行环境。

```bash
chatup remotion ./my-video --dry-run -I
chatup remotion ./my-video -I
chatup remotion ./my-video -I  # 再次验证已有项目，不覆盖源码
chatup remotion ./my-video --browser-executable /path/to/chrome -I
cd my-video
npm run studio
npm run render -- --browser-executable='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
```

终端中省略目录会询问，默认建议当前目录下的 `remotion-video`；显式目录直接执行。`-i` 强制询问，`-I` 禁止询问；无终端或 `CHATARCH_AUTO_PROMPT=0` 时缺少目录会报错。`--dry-run` 只预览，不运行 Node/npm、不联网、不创建目录。`--log-level` 支持 `DEBUG|INFO|WARNING|ERROR`，默认 `INFO`。

首次安装在目标目录旁暂存模板并执行 `npm ci --ignore-scripts --include=optional --no-audit --no-fund`，验证四个直接依赖版本后才移入目标路径。依赖仅安装到项目，不运行依赖生命周期脚本；失败时清理暂存目录。已有无关目录、文件和目标符号链接会被拒绝。ChatUp 通过 `.chatup-remotion.json` 识别自己创建的项目；再次运行只验证，不重装依赖或修改用户源码。依赖被修改或缺失时返回错误，用户可在项目中自行修复，不会自动覆盖。

初始化检测已安装的 Chrome/Chromium，或接受 `--browser-executable PATH`，并输出使用该浏览器的渲染命令。不启动 Studio、不下载浏览器；没有本机浏览器时仍可创建项目，并提示先用 `chatup chrome` 安装。直接运行不带浏览器参数的 Remotion render 可能由 Remotion 下载浏览器。macOS 可先运行 `chatup macos --app chrome --app blender` 准备桌面工具；Remotion 项目应放在自己的项目目录。

真实安装与 MP4 渲染已在 Apple Silicon macOS、Node 24.21.0、npm 11.19.0 验证；其他系统使用相同的 Node/npm 项目流程，原生安装与渲染尚未逐个平台实测。

## Chrome、Snipaste 与 iTerm2 {#chrome-iterm}

`chatup chrome` 安装普通 Google Chrome；`chatup snipaste` 在 macOS 或 Windows 安装 Snipaste；`chatup iterm` 安装 iTerm2，且仅限 macOS。

| 系统 | Chrome 安装路径 | Snipaste | iTerm2 |
| --- | --- | --- | --- |
| macOS Intel / Apple Silicon | Google 官方 universal stable DMG，无需 Homebrew | Snipaste 官方 DMG | iTerm2 官方 stable ZIP |
| Windows | WinGet 精确选择 `Google.Chrome.EXE`，当前用户 silent 安装 | WinGet 精确选择 `liule.Snipaste`，silent 安装 | 不支持，返回错误 |
| Linux x86_64 | 官方 stable DEB（apt-get）或 RPM（dnf/yum/zypper） | 不支持，返回错误 | 不支持，返回错误 |
| Linux ARM / 其他系统 | 明确返回不支持错误 | 不支持，返回错误 | 不支持 |

```bash
chatup chrome
chatup snipaste
chatup iterm
chatup chrome --dry-run
chatup snipaste --dry-run
chatup iterm --dry-run
chatup chrome --sudo --yes   # Linux 允许 sudo 并自动确认包安装
chatup chrome --yes          # Windows 明确接受来源和包协议
chatup snipaste --yes        # Windows 明确接受来源和包协议
```

三个命令支持 `--log-level DEBUG|INFO|WARNING|ERROR`；没有必填参数，不会触发补参交互。`--dry-run` 只检查本机平台/路径并打印计划，不联网、不执行安装程序、不写目录。

macOS 优先复用 `/Applications` 或 `~/Applications` 中已有的应用，否则安装到可写的 `/Applications`，不可写时回退到 `~/Applications`。下载后校验 bundle ID、版本、可执行文件、最低 macOS 版本和官方 Developer ID 签名，再暂存复制并原子移入目标位置。已有异常应用会报错，不覆盖；不会自动升级、启动、登录或更改默认浏览器/终端。安装缓存暂存于 `~/.chatarch/cache/desktop`（遵循 `CHATARCH_HOME`），完成后清理并卸载 DMG。

Linux 需要对应系统包管理器；普通用户必须显式提供 `--sudo`，否则安装前返回操作提示，root 可直接安装。包管理器负责依赖和系统要求，安装后回读 `google-chrome --version`。Windows 安装需要 [WinGet](https://aka.ms/getwinget)，安装前后按精确包 ID 回读 `Google.Chrome.EXE` 或 `liule.Snipaste`，不自动升级已有应用。Chrome 使用带版本号的官方 EXE，保留 WinGet 哈希校验，避免浮动 MSI 下载地址与清单不同步；安装后还会验证 `chrome.exe` 的有效 Google LLC 签名、产品身份及版本。标准用户或系统目录中已有的有效 Chrome 可直接复用，无需重新安装；无效程序或仅有登记记录而缺少程序时返回错误。

这些桌面安装入口不写 CFT/ChromeDriver/Playwright metadata、浏览器 profile 或 Cookie。自动化制品继续使用各自的独立 backend。

来源：[Google Chrome](https://www.google.com/chrome/)、[Snipaste](https://www.snipaste.com/)、[iTerm2 下载](https://iterm2.com/downloads.html)。

## ChatGPT 桌面应用 {#chatgpt-desktop}

`chatup chatgpt` 安装官方新版 ChatGPT 桌面应用，包含 Codex。它不是 `chatup codex`（Codex CLI），也不安装 ChatGPT Classic 或已弃用的 `codex-app`。

| 平台 | 安装来源 | 前提 |
| --- | --- | --- |
| macOS | `brew install --cask homebrew/cask/chatgpt` | 已安装 [Homebrew](https://brew.sh/)，系统与架构要求由当前 cask 检查 |
| Windows | `winget install --id 9PLM9XGG6VKS --exact --source msstore` | PATH 中有 WinGet，允许访问 Microsoft Store |
| Linux | [官方 Linux preview 安装说明](https://learn.chatgpt.com/docs/linux/linux-app) | ChatUp 暂不自动化 Linux 安装，不执行 sudo、软件源配置或整机升级 |

```bash
chatup chatgpt --dry-run  # 只显示当前系统的安装命令，不联网、不下载
chatup chatgpt            # 安装桌面应用
chatup chatgpt --yes      # Windows：明确接受 Microsoft Store 来源和包协议
```

Windows 使用非交互安装；首次安装若需要接受 Store 协议，请使用 `--yes`。macOS 上该标志不改变安装行为。缺少包管理器时返回安装指引，不自动 bootstrap Homebrew/WinGet。已有包管理器登记的安装会跳过，不自动升级（Windows 使用 `--no-upgrade`）；若 macOS 仍登记旧 `1.x` ChatGPT Classic，会明确要求手动迁移，而不冒充新版安装成功。手动安装导致冲突时交给包管理器报错，不强制覆盖。

成功表示包管理器安装记录已经回读确认，不代表应用已启动或登录。应用目录、下载缓存和运行数据由 Homebrew/Microsoft Store 与官方应用管理，使用原生平台布局（macOS 通常为 `/Applications/ChatGPT.app`），而不是 ChatArch 服务目录。ChatUp 不写桌面应用登录态，不更改 Codex CLI 配置；安装后请手动打开 ChatGPT 并登录。

Python 调用不需要经由 CLI：

```python
from chatup.setup.chatgpt import plan_chatgpt_install, setup_chatgpt

plan = plan_chatgpt_install()  # 纯计划，不要求本机已有包管理器
result = setup_chatgpt(dry_run=True)
# 真正安装：setup_chatgpt(yes=True)
```

返回值含 `app`、`platform`、`manager`、`package`、`command`、`verify_command`；安装 API 另含 `status`（`planned` / `already_installed` / `installed`）和 `verified`。失败或超时抛出 `RuntimeError`，CLI 非零退出；超时后先检查包管理器状态再重试。

来源：[OpenAI 下载页](https://chatgpt.com/download/)、[Windows 官方安装指引](https://learn.chatgpt.com/docs/windows/windows-app)、[Homebrew ChatGPT](https://formulae.brew.sh/cask/chatgpt)。

## Codex 命令约定

`chatup codex` 配置 OpenAI Codex CLI（默认 `~/.codex/config.toml` 与 `~/.codex/auth.json`；设置 `CODEX_HOME` 时使用该原生配置目录）：

默认模型为 `gpt-5.6-terra`（GPT-5.6 Terra），仅在没有可用的模型配置时兜底。显式 `--model`、所选 OpenAI profile，以及未显式选择 profile 时的已有 Codex 配置、进程环境和 active profile 仍按原优先级生效；不会把用户已配置的模型强制覆盖成默认值。

- `-e, --env VALUE` 是凭据来源：`VALUE` 是文件路径时按 env 文件读取，否则按 ChatEnv `OpenAI` profile 名读取。
- 当 `-e PROFILE` 选择 ChatEnv profile 时，ChatUp 只读取这个显式 profile，不会从 active profile、既有 Codex 配置或进程环境变量回填缺失的 secret；profile 文件按无插值方式读取，包含 `${...}` 这类未解析变量会失败而不会回填进程环境。
- ChatEnv profile 名不能包含路径分隔符、`.` 或 `..`；如果要传文件路径，该路径必须真实存在。
- 如果显式 profile 缺少 `OPENAI_API_KEY`，非交互 setup 会失败，不会把另一个账号的 key 写进 Codex。
- 模型、provider 与 API 登录方式写入 `config.toml` 的 root-level `model`、`model_provider`、`forced_login_method = "api"`，provider 细节写入 `[model_providers.crs]`（包括 `requires_openai_auth = true`）；旧的 root-level `preferred_auth_method` 会被替换。API key 只更新 `auth.json` 的 root-level `OPENAI_API_KEY`。既有的其他配置表和认证 JSON 字段会保留，不会迁移或打印登录凭据。
- Codex CLI 0.144+ 要求 `wire_api = "responses"`；`chatup codex` 写出的 CRS/OpenAI-compatible provider 使用 responses wire API。
- 模型渠道要通过 Codex 本身验证，例如先 `chatup codex -e apple -I`，再 `codex exec ...`；只 curl API 成功不等于 Codex 路由可用。

常用形式：

```bash
chatup codex -e apple -I
chatup codex -e ~/.chatarch/envs/OpenAI/.env -I
chatup codex --api-key "$OPENAI_API_KEY" --base-url https://example.invalid/openai/v1 --model gpt-5.6-terra -I
```

## Windows 原生安装与边界

Windows 10/11 的独立 Python 环境准备请先使用 ChatUV bootstrap；`chatup` 本身需要 Python >=3.10。安装 ChatUp 后：

```powershell
chatup nodejs -I
chatup codex -e work -I
chatup opencode -e work -I
chatup cursor-agent --install-only -I
```

`chatup nodejs` 检测到已有 Node >=20/npm 时复用；缺少时下载官方 LTS Windows ZIP，校验 SHA-256，安全解压至有效 `CHATARCH_HOME` 下，并把受管 Node 与 npm prefix 写入当前用户 PATH（不改系统 PATH）。直接运行 Codex/OpenCode 等 npm 工具安装命令也会完成用户 PATH 写入，不必先执行 `chatup nodejs`。现有进程仅前置受管目录，保留 Python 和系统 PATH。运行时选择先排除无法调用 npm 的候选，再比较版本；新终端可读取持久化的用户 PATH。通过共享的 `node.exe + npm-cli.js` 运行 npm，避免直接执行 `npm.cmd` 造成路径/参数错误；Codex、OpenCode、Claude、CC Connect、Lark CLI、Playwright 和 Remotion 使用此共享能力。

Cursor Agent 使用其官方 Windows PowerShell 安装器，Hermes 使用 ChatArch fork 的 Windows `install.ps1`，先确认实际 home/install 目标，再非交互安装，不默认启动 gateway/WebUI。当前官方 Cursor 安装器会重建 `%LOCALAPPDATA%\\cursor-agent`；ChatUp 在该目录已存在时拒绝自动执行，避免删除既有用户数据，需先自行迁移并确认后重试。ChatUp 不读取或迁移现有认证资料。Windows 配置及 native 安装的验收限于 CI 矩阵、受管 Node/Codex/OpenCode smoke、Hermes 路径只读探针；不包含真实用户登录或模型请求。

`iterm` 和 `macos` 为 macOS-only，`zsh` 为 POSIX-only，`crs` 当前为 POSIX 服务路径；`glance` 当前只有 Linux amd64 release asset。Gitea、MySQL、Twikoo 和 NGINX 的 Windows 二进制/配置能力与 systemd service/start 分开，后者不宣称原生 Windows 可用。Discourse/Zulip 的 Docker 配置不是 Docker Desktop 服务验收。细分范围见 capability map。

## Cursor Agent 命令约定

`chatup cursor-agent` 面向 Cursor Agent CLI，而不是 Cursor IDE GUI：

- `--auth-json PATH` 复制包含 `accessToken` / `refreshToken` 的 Cursor `auth.json`；
- `--auth-env PATH` 从 env 文件读取 `CURSOR_ACCESS_TOKEN` 和 `CURSOR_REFRESH_TOKEN` 后写成 Cursor JSON；
- `-e, --env VALUE` 快速读取 Cursor 凭据：`VALUE` 是文件路径时按 env 文件读取，否则按 ChatEnv `CursorAgent` profile 名读取；
- `--env-profile NAME` 从 ChatEnv `CursorAgent` profile 读取 token 并写成 Cursor JSON；
- `--save-profile NAME` 把导入的 token 保存到 ChatEnv `CursorAgent` profile，不打印 secret 值；
- `--cli-config PATH` 复制 `~/.cursor/cli-config.json`；
- `--agent-state PATH` 复制 `~/.cursor/agent-cli-state.json`；
- `--api-key-env NAME` 仅把指定环境变量作为验证时的 `CURSOR_API_KEY`，不会把 secret 放进 argv；
- `--credential-store file-wrapper` 会写入不含 token 的 `cursor-agent` wrapper，在运行时从 `auth.json` 读取 token 并使用文件登录态，适合把 Linux `auth.json` 迁移到 macOS；
- 写入 Cursor 自身登录态/配置文件时会使用受限权限；ChatEnv `CursorAgent` profile 由 ChatEnv 自己的存储机制维护，ChatUp 不额外改 profile `.env` 权限。

常用形式：

```bash
chatup cursor-agent --install-only -I
chatup cursor-agent --auth-json ./auth.json --cli-config ./cli-config.json --agent-state ./agent-cli-state.json --credential-store file-wrapper -I
chatup cursor-agent -e ./cursor.env --credential-store file-wrapper -I
chatup cursor-agent --auth-env ./cursor.env --save-profile work --credential-store file-wrapper -I
chatup cursor-agent -e work --credential-store file-wrapper -I
```

## 本地服务

| 命令 | 当前能力 |
|---|---|
| `chatup gitea` | 从 `ChatArch/gitea` Release assets 安装 ChatArch Gitea；默认跟随 latest，可选生成 ChatTea-compatible `app.ini` 和 user-level systemd service。 |
| `chatup glance` | 安装并初始化已校验的 `ChatArch/glance` Linux amd64 本地运行时；不启动服务或写入凭据。 |
| `chatup discourse` | 准备 `~/.chatarch/discourse` 下的 Discourse Docker/app.yml 布局，并从 ChatEnv 读取 `DISCOURSE_ADMIN_USERNAME`、`DISCOURSE_ADMIN_EMAIL`、`DISCOURSE_ADMIN_PASSWORD` 写入受限权限的 `secrets/admin.env`。 |
| `chatup zulip` | 准备 `~/.chatarch/zulip` 下的 Zulip Docker Compose、bind-mount 数据目录和 secret files，并从 ChatEnv 读取 `ZULIP_ADMIN_USERNAME`、`ZULIP_ADMIN_EMAIL`/`ZULIP_ADMIN_MAIL`、`ZULIP_ADMIN_PASSWORD`。 |
| `chatup mysql` | 安装并准备 ChatData-compatible user-level MySQL runtime、实例目录、`my.cnf` 和可选 user-level systemd service。 |
| `chatup twikoo` | 从 `twikoojs/twikoo` Release assets 安装 Twikoo 二进制，并准备多实例目录、实例 env、实例级 `bin/twikoo` 和可选 user-level systemd service。 |
| `chatup nginx` | 准备 `~/.chatarch/nginx` 下的 user-level NGINX runtime/config/log/run/temp 布局，也可生成 reverse-proxy、HTTPS proxy、WebSocket proxy、static root 和 redirect 模板。 |
| `chatup crs` | 安装本地 Claude Relay Service，准备 Redis、配置、secret、admin SPA 和 smoke check。 |

## 工作区

| 命令 | 当前能力 |
|---|---|
| `chatup workspace` | 初始化 ChatArch 人类-AI 协作 workspace。 |

## 浏览器制品 backend 约定

`chatup chrome` 安装普通桌面浏览器。自动化制品仍由独立 backend 管理：

- `chatup chrome-for-testing` 管理真正可启动的 Google Chrome for Testing 浏览器，默认 home 为 `~/.chatarch/chrome-for-testing`；
- `chatup chromedriver` 管理 ChromeDriver WebDriver server，默认 home 为 `~/.chatarch/chromedriver`；
- `chatup playwright` 管理精确 Playwright package 与 Playwright Chromium，默认 home 为 `~/.chatarch/playwright`；
- Chrome for Testing 与 ChromeDriver 各自提供完整制品生命周期；Playwright 仅提供本任务实际使用的 `install/path/doctor`；
- `Chrome for Testing` 中的 Testing 是官方制品名，不是用户 CLI 的 `test` 操作；
- `chromium` 尚无已验证 provider，因此不注册命令；
- 安装使用官方 HTTPS manifest、可选 SHA-256、受限 ZIP 解压、`installation.json` 和原子目录替换；
- `remove` 需要 `--yes`，`gc` 默认 dry-run，apply 同时需要 `--yes`；
- 不修改系统 Chrome、不创建 Profile/Cookie，也不管理账号或扩展。

```bash
chatup chrome-for-testing install --channel stable -I
chatup chrome-for-testing path 145.0.7632.6 -I
chatup chromedriver install --match-cft-version 145.0.7632.6 -I
chatup chromedriver doctor 145.0.7632.6 --output json -I
chatup playwright install 1.61.1 --output json -I
chatup playwright path 1.61.1 -I
```

完整子命令、ChatStyle 行为和 Python contract 见 [CLI 树](cli-tree.md)。

## Gitea 命令约定

`chatup glance` 裸命令就是安装入口：默认解析 `ChatArch/glance` 最新稳定维护版，也可用 `--version chatarch-vMAJOR.MINOR.PATCH` 严格固定版本。当前发布矩阵仅含 Linux amd64；安装前会拒绝其他平台。安装器只下载对应归档、`SHA256SUMS`、`BUILDINFO.txt`，验证归档与 BUILDINFO 摘要、tag、source SHA、平台和二进制原始版本，再由 ChatGlance portable API 安全解包并初始化 loopback 配置。

```bash
chatup glance
chatup glance --version chatarch-v0.2.1 --runtime-home ~/.chatarch/glance -I
chatup glance --dry-run
```

结果会打印 binary、config 和精确原生启动命令。安装器不自动启动/启用服务或建立公网入口，不生成认证 fixture/明文密码。重复执行只复用精确 provenance；保留 config、pages、notes、data、accounts 和 timers。已有版本不匹配或来源不可验证时拒绝替换，请显式使用原生 `chatglance runtime update`。

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

## Discourse / Zulip 命令约定

`chatup discourse` 和 `chatup zulip` 面向 ChatArch 社区服务安装，不在命令输出中打印管理员密码。管理员凭据统一来自 ChatEnv：

```text
DISCOURSE_ADMIN_USERNAME
DISCOURSE_ADMIN_EMAIL
DISCOURSE_ADMIN_PASSWORD
ZULIP_ADMIN_USERNAME
ZULIP_ADMIN_EMAIL      # 或兼容 ZULIP_ADMIN_MAIL
ZULIP_ADMIN_PASSWORD
```

常用形式：

```bash
chatup discourse -e discourse-prod --hostname discourse.public.wzhecnu.cn
chatup discourse -e ./discourse-admin.env --clone --force
chatup zulip -e zulip-prod --external-host zulip.public.wzhecnu.cn --port 3095
chatup zulip -e ./zulip-admin.env --pull --start
```

默认行为：

- `chatup discourse` 准备 `~/.chatarch/discourse`、`docker/containers/app.yml`、`shared/standalone` 和 `secrets/admin.env`；`--clone` 才 clone/update `discourse_docker`。
- `chatup zulip` 准备 `~/.chatarch/zulip/compose/compose.yaml`、`data/` bind mounts、`secrets/` secret files 和 `secrets/admin.env`；`--start` 才执行 Docker Compose。
- Zulip Compose 默认只绑定 `127.0.0.1:3095:80`，不抢主机 `25/80/443`；public/local 入口仍交给外层 NGINX/public-entry。
- `ZULIP_ADMIN_MAIL` 只作为 `ZULIP_ADMIN_EMAIL` 的兼容别名；优先使用 `ZULIP_ADMIN_EMAIL`。

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

## Twikoo 命令约定

`chatup twikoo` 面向 Twikoo 评论服务的 no-Docker、多实例安装：

- 默认 Twikoo 版本：`1.7.15`。
- 默认 repo：`twikoojs/twikoo`。
- 默认 home：`~/.chatarch/twikoo`。
- 默认实例：`chatblog`。
- 默认端口：`8892`。
- 默认绑定：`127.0.0.1`。
- 默认会下载 release 二进制、初始化实例目录、生成 `env/twikoo.env` 并写入 user-level systemd service，但不会启动服务。
- 每个实例都通过 `instances/<name>/bin/twikoo` 启动，并让 `bin/.env` 指向该实例自己的 `env/twikoo.env`；不要让多个实例直接共享 runtime 目录旁边的 `.env`。
- local/public 域名入口仍由 NGINX/public-entry 管理。

常用形式：

```bash
chatup twikoo --name chatblog --port 8892
chatup twikoo --name chatblog --port 8892 --start --smoke
chatup twikoo --home ~/.chatarch/twikoo --name another-blog --port 8893 --no-start
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
