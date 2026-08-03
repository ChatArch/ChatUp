# ChatUp 文档

ChatUp 是 ChatArch 的独立安装与初始化 CLI，用来把一台机器整理成可执行 ChatArch 工作流的本地环境。

它的目标不是成为通用包管理器，而是把 ChatArch 常用的环境准备步骤收敛成可复用、可测试、可审查的一级命令。

站点入口：https://arch.gh.wzhecnu.cn/ChatUp/

## 按场景选择文档

| 场景 | 文档 |
| --- | --- |
| 从空机器验证 ChatUp、Python runtime 和 workspace | [快速开始](quickstart.md) |
| 查看完整一级 CLI 树和 CFT/ChromeDriver 独立 contract | [CLI 树](cli-tree.md) |
| 查看命令分组、参数边界和服务默认路径 | [命令参考](commands.md) |
| 校对哪些 ChatArch setup 流程已经有一等命令 | [CLI 能力地图](capability-map.md) |
| 理解 `chatup workspace` 创建的目录和项目记录约定 | [工作区脚手架](workspace.md) |
| 安装 ChatTea-compatible Gitea、ChatData-compatible MySQL、user-level NGINX 和 CRS | [命令参考](commands.md) |
| 确认 ChatArch 默认目录、安全边界和交互约定 | [CLI 能力地图](capability-map.md) |

## 文档栏目组织

当前文档按任务和能力拆成多个入口，避免把所有安装步骤写成一条线性清单：

- **入门**：从安装 ChatUp、`doctor`、`uv` 和 workspace 初始化开始。
- **CLI / 能力地图**：列出真实已实现命令、命令分组和当前边界。
- **本地服务**：说明 Gitea、MySQL、NGINX、CRS 的 user-level 默认目录和安全约定。
- **工作区**：说明 ChatArch workspace scaffold 和项目记录结构。
- **安全边界**：说明本地监听、secret 文件、`~/.chatarch/...` 默认路径和不负责的系统级范围。

## 核心入口

<div class="grid cards" markdown>

- **快速开始**

    从 editable install、`chatup doctor`、`chatup uv` 和工作区初始化开始，快速验证本机环境。

    [进入快速开始](quickstart.md)

- **命令参考**

    查看带注释的 CLI 树、命令分组、服务安装默认路径和本地安全约定。

    [查看命令参考](commands.md)

- **CLI 树**

    查看全部一级命令，以及独立 CFT/ChromeDriver 安装、JSON 输出和 Python descriptor 契约。

    [查看 CLI 树](cli-tree.md)

- **CLI 能力地图**

    像 ChatTea 的能力地图一样，按职责校对当前一等命令、默认目录和不负责的边界。

    [查看能力地图](capability-map.md)

- **工作区脚手架**

    理解 `chatup workspace` 创建的 ChatArch workspace 目录、记录和协作约定。

    [查看工作区说明](workspace.md)

</div>

## 适用场景

<div class="grid cards" markdown>

- **新机器初始化**

    安装 Python、Node.js、Docker 检查、独立 Chrome for Testing/ChromeDriver backend 和 shell 基础环境。

- **工作区初始化**

    生成人类-AI 协作 workspace 结构，包括 `projects/`、`core/`、`skills/` 和 `public/`。

- **Agent 工具链配置**

    配置 Claude Code、Codex、OpenCode、Hermes、CC Connect 和飞书工具链。

- **本地服务准备**

    安装 ChatArch Gitea、ChatData-compatible MySQL、Claude Relay Service、FRP，准备 user-level NGINX，并生成入口模板。

</div>

## 安全默认值

<div class="grid cards" markdown>

- **本地优先**

    服务类命令默认绑定 `127.0.0.1`，公网入口交给 NGINX/public-entry 层。

- **ChatArch 目录**

    新增安装项默认落在 `~/.chatarch/...`，避免散落到系统目录。

- **敏感值不回显**

    ChatUp 可以生成本地配置和 secret 文件，但不会把敏感值打印到终端。

</div>

## CLI

```bash
chatup --help
chatup chrome-for-testing --help
chatup chromedriver --help
chatup gitea --help
chatup mysql --help
chatup nginx --help
```

完整一级命令树见 [CLI 树](cli-tree.md)，详细命令约定见 [命令参考](commands.md)，按能力分组的简明地图见 [CLI 能力地图](capability-map.md)。

## 设计边界

- ChatUp 负责安装、初始化和本地配置，不负责长期运行时编排。
- 需要交互的命令遵循 `-i` / `-I` 约定：`-i` 强制交互，`-I` 禁止提示并快速失败。
- 面向服务的命令优先使用本地安全默认值，例如绑定 `127.0.0.1`、任务本地目录和受限文件权限。
