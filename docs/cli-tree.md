# CLI 树

ChatUp 采用扁平的一等安装命令。每个顶层命令负责一种明确的机器环境、工具链或本地服务，不再额外增加 `setup` 或 `browser` 中间层。

## 顶层命令

```text
chatup
├── doctor       # 验证 ChatUp CLI 可调用
├── uv           # 安装 uv 和 ~/.chatarch/venv
├── workspace    # 初始化 ChatArch workspace
├── nodejs       # 安装 nvm 与默认 LTS Node.js
├── docker       # 检查 Docker 环境与权限
├── zsh          # 配置 zsh、插件和 alias
├── chrome       # 安装 ChatArch 内部 Chrome for Testing
├── frp          # 安装 FRP Client/Server
├── gitea        # 安装 ChatTea-compatible Gitea
├── mysql        # 安装 ChatData-compatible MySQL
├── nginx        # 准备 user-level NGINX
├── crs          # 安装本地 Claude Relay Service + Redis
├── cc-connect   # 安装 ChatArch CC Connect
├── claude       # 安装/配置 Claude Code
├── codex        # 安装/配置 Codex CLI
├── opencode     # 安装/配置 OpenCode
├── hermes       # 安装 Hermes Agent 与可选 WebUI
└── lark-cli     # 配置官方 lark-cli 与 ChatEnv
```

完整参数见 [命令参考](commands.md)。

## 为什么 Chrome 是独立命令

Chrome 是机器环境依赖，和 `uv`、`nodejs`、`docker` 属于同一层级。ChatUp 负责安装；消费方只解析安装结果。

因此不设计：

```text
chatup browser install chrome
chatpost browser install chrome
```

而是统一使用：

```bash
chatup chrome
```

这让 ChatPost、ChatBlog 自动化或其他包都可以复用同一个环境，不需要把 Chrome 下载逻辑绑定到某个产品的 Browser Runner 模型。

## `chatup chrome` 契约

```text
chatup chrome
├── --version VERSION          # stable/beta/dev/canary 或精确版本
├── --home PATH                # 默认 ~/.chatarch/chrome
├── --platform PLATFORM        # 默认自动识别
├── --sha256 HEX               # 可选 expected archive digest
├── --force                    # 原子替换同版本安装
├── --doctor / --no-doctor     # 是否执行 version probe
├── --output text|json         # 人类或机器输出
└── -i / -I                    # ChatStyle 交互策略
```

默认安装布局：

```text
~/.chatarch/chrome/
└── chrome-for-testing/
    └── <version>/
        └── <platform>/
            ├── runtime.json
            └── <vendor archive tree>/
```

这个命令：

- 从 Chrome for Testing 官方 manifest 解析 channel 或精确版本；
- 支持 `mac-arm64`、`mac-x64`、`linux64` 和 `win64`；
- 下载到临时目录，检查 HTTPS 来源、可选 SHA-256 和 ZIP 路径安全；
- 完成后原子切换目录，不破坏已有可用安装；
- 不修改系统 Chrome；
- 不安装到 `~/.local/bin`；
- 不要求 Docker；
- 不创建浏览器 Profile、不加载扩展、不保存 Cookie。

## JSON 输出

`--output json` 是下游程序的稳定边界：

```json
{
  "ref": "chrome-for-testing@<resolved-version>",
  "kind": "chrome-for-testing",
  "version": "<resolved-version>",
  "platform": "mac-arm64",
  "root_dir": "~/.chatarch/chrome/chrome-for-testing/<version>/mac-arm64",
  "binary_path": "<absolute executable path>",
  "source_url": "https://...",
  "archive_sha256": "<sha256>",
  "installed_at": "<timestamp>",
  "status": "ready"
}
```

机器调用不能解析彩色文本或日志来寻找 executable。

## Python 接口

Python 消费方优先使用 importable API，而不是 shell out：

```python
from chatup.chrome import ensure_chrome, resolve_chrome

runtime = ensure_chrome(version="<tested-version>")
print(runtime.binary_path)
```

`ensure_chrome` 可以安装缺失的精确版本；`resolve_chrome` 只读取已有 `runtime.json`，不做网络写入。

## 与 ChatPost 的边界

ChatUp 返回：

```text
binary_path
version
platform
runtime root
provenance/digest
health status
```

ChatPost 继续负责：

```text
isolated user-data-dir
Runner process / port / lock
extension and bridge
manual login checkpoint
platform account mapping
publication ledger
```

Chrome 安装不再是 ChatPost CLI 的一部分。
