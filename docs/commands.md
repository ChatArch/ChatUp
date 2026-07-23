# 命令参考

本页只列当前已经实现的 `chatup` 一级命令。运行时以 `chatup <command> --help` 为准。

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
| `chatup gitea` | 从 `ChatArch/gitea` Release assets 安装 ChatArch Gitea 二进制。 |
| `chatup crs` | 安装本地 Claude Relay Service，准备 Redis、配置、secret、admin SPA 和 smoke check。 |

## 工作区

| 命令 | 当前能力 |
|---|---|
| `chatup workspace` | 初始化 ChatArch 人类-AI 协作 workspace。 |

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
