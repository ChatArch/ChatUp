# ChatUp

ChatUp 是 ChatArch 的独立环境与工具安装 CLI。它承接原来 `chattool setup` 的职责，把常用开发环境、Agent CLI、工作区脚手架和本地服务安装整理成一级命令，例如 `chattool setup workspace` 对应 `chatup workspace`。

- 文档站：<https://arch.gh.wzhecnu.cn/ChatUp/>
- English README: [README.en.md](README.en.md)
- Source: <https://github.com/ChatArch/ChatUp>

按场景选择文档：

| 场景 | 文档 |
| --- | --- |
| 从空机器验证 ChatUp、Python runtime 和 workspace | `docs/quickstart.md` |
| 阅读完整顶层 CLI 树和独立 CFT/ChromeDriver/Playwright contract | `docs/cli-tree.md` |
| 查看命令分组、参数边界和服务默认路径 | `docs/commands.md` |
| 校对哪些 ChatArch setup 流程已经有一等命令 | `docs/capability-map.md` |
| 理解 `chatup workspace` 创建的目录和项目记录约定 | `docs/workspace.md` |
| 安装 ChatTea-compatible Gitea、Discourse/Zulip 社区服务配置、ChatData-compatible MySQL、user-level NGINX 和 CRS | `docs/commands.md` |

## 快速开始

```bash
chatup --help
chatup --version
chatup --tree
chatup --tree-brief
chatup doctor
chatup uv
chatup chrome-for-testing install --channel stable -I
chatup playwright install 1.61.1 -I
chatup workspace ~/Playground
```

`chatup uv` 默认更新已有 `~/.bashrc`、`~/.zshrc` 的自动激活块；使用 `chatup uv --no-activate` 可保持启动配置不变。不会创建缺失的 rc 文件，Windows 跳过此项。

常见安装命令：

```bash
chatup gitea --force
chatup discourse -e discourse-prod --hostname discourse.public.wzhecnu.cn
chatup zulip -e zulip-prod --external-host zulip.public.wzhecnu.cn --port 3095
chatup mysql
chatup nginx
chatup nginx proxy-pass ./gitea-local.conf --set SERVER_NAME=gitea.local.example.invalid --set PROXY_PASS=http://127.0.0.1:3000
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

## macOS 常用应用

```bash
chatup macos                       # 勾选安装，Apple Silicon 默认全选四项
chatup macos --app snipaste         # 只安装 Snipaste
chatup macos --app blender          # 安装 Blender 5.2.2 LTS（Apple Silicon）
chatup macos -I                    # 不询问，安装当前机器支持的全部选项
chatup macos --dry-run             # 只预览安装计划
```

仅限 macOS。Apple Silicon 默认勾选 Snipaste、iTerm2、Chrome、Blender；Intel 保持前三项。终端中用空格切换勾选，回车安装；取消全部勾选则直接退出。可重复传入 `--app snipaste|iterm|chrome|blender` 选择多个应用。直接使用官方安装包，无需 Homebrew，已有应用验证后复用。详见[macOS 安装入口](https://arch.gh.wzhecnu.cn/ChatUp/commands/#macos)。

## Remotion 视频项目

```bash
chatup remotion ./my-video --dry-run -I
chatup remotion ./my-video -I
cd my-video
npm run studio
```

需要已有 Node.js >=18.12 和 npm >=9。创建带锁文件的 Remotion 4.0.530 项目，检测本机 Chrome 并输出渲染命令；不覆盖已有无关目录，也不替换 Node 或下载浏览器。项目放在指定目录，已有 Blender/Chrome 可通过 `chatup macos --app blender --app chrome` 验证或安装。详见[Remotion 安装约定](https://arch.gh.wzhecnu.cn/ChatUp/commands/#remotion)。

## Chrome、Snipaste 与 iTerm2

```bash
chatup chrome --dry-run
chatup chrome             # 按系统安装普通 Google Chrome
chatup snipaste           # 在 macOS 或 Windows 安装 Snipaste
chatup iterm              # 安装 iTerm2，仅限 macOS
chatup chrome --sudo --yes # Linux：允许提权并确认包安装
```

macOS 直接下载官方 DMG/ZIP 并校验开发者签名，无需 Homebrew；默认装到 `/Applications`，不可写时使用 `~/Applications`。Windows 使用 WinGet 精确包 `Google.Chrome.EXE`（当前用户安装）和 `liule.Snipaste`，需以 `--yes` 接受首次协议，Chrome 还会验证已安装程序的 Google 签名、产品身份和版本；Linux x86_64 支持 Chrome 的官方 DEB/RPM 与 apt/dnf/yum/zypper。已安装时验证并复用，不改默认浏览器、终端或用户配置。自动化浏览器仍使用 `chatup chrome-for-testing`。详见[安装约定](https://arch.gh.wzhecnu.cn/ChatUp/commands/#chrome-iterm)。

## ChatGPT / Codex 桌面应用

```bash
chatup chatgpt --dry-run
chatup chatgpt
chatup chatgpt --yes  # Windows 首次安装时接受 Store 协议
```

安装包含 Codex 的新版官方 ChatGPT 桌面应用。macOS 需要 Homebrew，Windows 需要 WinGet；Linux preview 暂按[官方说明](https://learn.chatgpt.com/docs/linux/linux-app)手动安装。现有 `chatup codex` 仍安装/配置 Codex CLI。不会自动启动、登录或升级已有应用；[完整约定](https://arch.gh.wzhecnu.cn/ChatUp/commands/#chatgpt-desktop)。

`chatup codex`、`chatup hermes` 未配置模型时默认使用 `gpt-5.6-terra`；用户指定的模型和已有配置仍优先。

## 当前能力

| 能力组 | 命令 |
| --- | --- |
| 基础运行环境 | `doctor`、`uv`、`nodejs`、`docker`、`zsh`、`chrome-for-testing`、`chromedriver`、`playwright`、`frp` |
| 工作区脚手架 | `workspace` |
| 桌面应用 | `macos`（Snipaste/iTerm2/Chrome/Blender 多选）、`chrome`、`snipaste`（macOS/Windows）、`iterm`（仅 macOS）、`chatgpt`（含 Codex） |
| 视频项目 | `remotion` |
| 本地服务安装 | `gitea`、`discourse`、`zulip`、`mysql`、`nginx`、`crs` |
| Agent 工具链 | `cc-connect`、`claude`、`codex`、`cursor-agent`、`opencode`、`hermes`、`lark-cli` |

桌面应用使用系统原生应用目录；ChatArch 自管安装项默认目录收敛到 `~/.chatarch/...`，例如 `~/.chatarch/chrome-for-testing`、`~/.chatarch/chromedriver`、`~/.chatarch/playwright`、`~/.chatarch/chattea`、`~/.chatarch/discourse`、`~/.chatarch/zulip`、`~/.chatarch/chatdata`、`~/.chatarch/nginx` 和 `~/.chatarch/crs/local`。`cursor-agent` 额外注册 ChatEnv `CursorAgent` profile，`discourse`/`zulip` 注册管理员凭据 profile，并支持 `-e/--env` 从 env 文件或 profile 快速配置；显式选择 profile 时不会混入进程环境中的其他账号凭据。CLI 树由 ChatStyle 的注册表渲染。更完整的能力边界见 `docs/capability-map.md`。

## 开发

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
mkdocs build --strict
chatup --version
chatup --tree
chatup --tree-brief
```

更多使用说明见文档站的 [快速开始](https://arch.gh.wzhecnu.cn/ChatUp/quickstart/)、[命令参考](https://arch.gh.wzhecnu.cn/ChatUp/commands/) 和 [CLI 能力地图](https://arch.gh.wzhecnu.cn/ChatUp/capability-map/)。

## 发布

发布由 tag 驱动。`vX.Y.Z` tag 必须与 `src/chatup/__init__.py::__version__` 一致；发布 workflow 会通过 PyPI Trusted Publishing/OIDC 构建并发布到 PyPI。
