# 快速开始

## 推荐路径

<div class="grid cards" markdown>

- **基础环境**

    先安装 ChatUp，再用 `chatup doctor`、`chatup uv` 检查 CLI 和 Python 运行环境；需要浏览器自动化时再运行 `chatup chrome`。

- **工作区**

    用 `chatup workspace default ~/Playground` 初始化 ChatArch 协作目录。

- **本地服务**

    按需准备 `gitea`、`mysql`、`nginx` 和 `crs`，默认都走 `~/.chatarch/...` 本地路径。

</div>

## 安装

从源码开发或本地验证时，使用 editable install：

```bash
python -m pip install -e .
chatup --version
chatup doctor
```

如果使用 ChatArch 默认运行环境，通常会安装到 `~/.chatarch/venv`：

```bash
~/.chatarch/venv/bin/python -m pip install -e .
~/.chatarch/venv/bin/chatup --help
```

## 初始化 Python 运行环境

```bash
chatup uv
```

默认行为：

- 安装或复用 `uv`。
- 创建 `~/.chatarch/venv`。
- 默认使用 Python 3.12。

如需自定义路径：

```bash
chatup uv --venv ~/.chatarch/venv --python-version 3.12
```

## 安装 Chrome 环境

```bash
chatup chrome
```

该命令把 Chrome for Testing 安装到 `~/.chatarch/chrome`，不会修改系统 Chrome。需要把结果交给其他程序时使用 JSON：

```bash
chatup chrome --version stable --output json -I
```

完整 option 和 Python 接口见 [CLI 树](cli-tree.md)。

## 初始化工作区

```bash
chatup workspace default ~/Playground
```

该命令会创建 ChatArch workspace 的基础结构，包括：

```text
AGENTS.md
projects/
archive/
core/
skills/
public/
.trash/
```

## 安装本地服务

安装 ChatArch Gitea：

```bash
chatup gitea --force
chatup gitea --init --service --base-url http://127.0.0.1:3000
```

准备 ChatData-compatible MySQL：

```bash
chatup mysql
chatup mysql --start --smoke
```

准备 user-level NGINX：

```bash
chatup nginx
```

生成 NGINX 反向代理配置：

```bash
chatup nginx proxy-pass ./gitea-local.conf \
  --set SERVER_NAME=gitea.local.example.invalid \
  --set PROXY_PASS=http://127.0.0.1:3000
```

安装本地 Claude Relay Service：

```bash
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

`chatup crs` 会准备本地 Redis 组件和 CRS 配置。默认 smoke check 需要服务启动；如果只想准备文件而不启动服务，请同时传入：

```bash
chatup crs --no-start --no-smoke
```

## 交互模式

ChatUp 使用统一交互约定：

- `-i`：强制进入交互提示。
- `-I`：禁用交互提示，适合 CI、脚本和自动化。
- 缺少可恢复参数时，命令可以自动提示；缺少不可恢复参数时应快速失败。
