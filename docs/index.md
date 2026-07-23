# ChatUp 文档

ChatUp 是 ChatArch 的独立安装与初始化 CLI，用来把一台机器整理成可执行 ChatArch 工作流的本地环境。

它的目标不是成为通用包管理器，而是把 ChatArch 常用的环境准备步骤收敛成可复用、可测试、可审查的一级命令。

## 适用场景

- 新机器初始化：安装 Python/Node.js 等基础运行环境。
- 工作区初始化：生成人类-AI 协作 workspace 结构。
- Agent 工具链配置：配置 Claude Code、Codex、OpenCode、Hermes、CC Connect 等工具。
- 本地服务准备：安装 ChatArch Gitea、Claude Relay Service、FRP 等组件。

## 设计边界

- ChatUp 负责安装、初始化和本地配置，不负责长期运行时编排。
- ChatUp 可以生成本地配置和 secret 文件，但不会把敏感值打印到终端。
- 需要交互的命令遵循 `-i` / `-I` 约定：`-i` 强制交互，`-I` 禁止提示并快速失败。
- 面向服务的命令优先使用本地安全默认值，例如绑定 `127.0.0.1`、任务本地目录和受限文件权限。

## 文档入口

- [快速开始](quickstart.md)
- [命令参考](commands.md)
- [工作区脚手架](workspace.md)
