# CLI 树

ChatUp 使用一等顶层命令，但不把不同浏览器制品强行统一成一个 `browser` 抽象。Chrome for Testing 浏览器和 ChromeDriver WebDriver server 各自拥有独立命令集、Python API、metadata 和存储目录。

## 顶层命令

```text
chatup
├── doctor              # 验证 ChatUp CLI 可调用
├── uv                  # 安装 uv 和 ~/.chatarch/venv
├── workspace           # 初始化 ChatArch workspace
├── nodejs              # 安装 nvm 与默认 LTS Node.js
├── docker              # 检查 Docker 环境与权限
├── zsh                 # 配置 zsh、插件和 alias
├── chrome-for-testing  # 管理 Google Chrome for Testing 浏览器
├── chromedriver        # 管理 ChromeDriver WebDriver server
├── frp                 # 安装 FRP Client/Server
├── gitea               # 安装 ChatTea-compatible Gitea
├── mysql               # 安装 ChatData-compatible MySQL
├── nginx               # 准备 user-level NGINX
├── crs                 # 安装本地 Claude Relay Service + Redis
├── cc-connect          # 安装 ChatArch CC Connect
├── claude              # 安装/配置 Claude Code
├── codex               # 安装/配置 Codex CLI
├── opencode            # 安装/配置 OpenCode
├── hermes              # 安装 Hermes Agent 与可选 WebUI
└── lark-cli            # 配置官方 lark-cli 与 ChatEnv
```

完整参数见 [命令参考](commands.md)。

## 制品身份

| Backend | 实际制品 | 角色 |
| --- | --- | --- |
| `chrome-for-testing` | Google Chrome for Testing | 可启动的浏览器；支持扩展和 CDP |
| `chromedriver` | ChromeDriver | WebDriver 协议 server；不是浏览器 |

`Chrome for Testing` 是 Google 官方发行名称。命令中的 `for-testing` 描述制品身份，不表示 ChatUp 暴露了一个 `test` 操作；两个 backend 都没有 `test` 子命令，健康检查统一叫 `doctor`。

当前不注册 `chatup chromium`。只有选定并验证真实 Chromium 下载源、revision contract、平台布局和验收方式后，才会新增独立 Chromium backend。

## Chrome for Testing

```text
chatup chrome-for-testing
├── install
│   ├── --version VERSION
│   ├── --channel stable|beta|dev|canary
│   ├── --platform PLATFORM
│   ├── --home PATH
│   ├── --sha256 HEX
│   ├── --force
│   ├── --doctor / --no-doctor
│   ├── --output text|json
│   └── -i / -I
├── list [--home PATH] [--output text|json]
├── show [VERSION] [--platform PLATFORM] [--output text|json] [-i|-I]
├── path [VERSION] [--platform PLATFORM] [--output text|json] [-i|-I]
├── doctor [VERSION] [--execute|--no-execute] [--output text|json] [-i|-I]
├── remove [VERSION] --yes [--output text|json] [-i|-I]
└── gc [--dry-run|--apply] [--yes] [--minimum-age-hours HOURS]
```

`install` 的 `--version` 与 `--channel` 互斥；都不提供时默认使用 stable。`resolve` 类操作只接受完整四段版本，不能使用 channel 或旧的 `chrome@...` / `cft@...` 引用。

```bash
chatup chrome-for-testing install --channel stable -I
chatup chrome-for-testing install --version 145.0.7632.6 --output json -I
chatup chrome-for-testing path 145.0.7632.6 -I
chatup chrome-for-testing doctor 145.0.7632.6 --output json -I
```

## ChromeDriver

```text
chatup chromedriver
├── install
│   ├── --version VERSION
│   ├── --channel stable|beta|dev|canary
│   ├── --match-browser PATH
│   ├── --match-cft-version VERSION
│   ├── --platform PLATFORM
│   ├── --home PATH
│   ├── --sha256 HEX
│   ├── --force
│   ├── --doctor / --no-doctor
│   ├── --output text|json
│   └── -i / -I
├── list [--home PATH] [--output text|json]
├── show [VERSION] [--platform PLATFORM] [--output text|json] [-i|-I]
├── path [VERSION] [--platform PLATFORM] [--output text|json] [-i|-I]
├── doctor [VERSION] [--execute|--no-execute] [--output text|json] [-i|-I]
├── remove [VERSION] --yes [--output text|json] [-i|-I]
└── gc [--dry-run|--apply] [--yes] [--minimum-age-hours HOURS]
```

四个安装选择器互斥。`--match-browser` 读取给定浏览器 binary 的 `--version`，先按 Google 官方 build manifest 匹配，找不到时退回 milestone manifest；浏览器 patch 与最终 Driver patch 不必相同。`--match-cft-version` 直接使用精确 CFT 版本。ChromeDriver 不参与 ChatPost 当前的扩展/CDP 知乎链路。

```bash
chatup chromedriver install --channel stable -I
chatup chromedriver install --match-cft-version 145.0.7632.6 -I
chatup chromedriver install --match-browser /path/to/browser --output json -I
```

## 独立存储

```text
~/.chatarch/
├── chrome-for-testing/
│   └── <version>/<platform>/
│       ├── installation.json
│       └── <Google archive tree>/
└── chromedriver/
    └── <version>/<platform>/
        ├── installation.json
        └── <Google archive tree>/
```

两个 backend 都使用官方 HTTPS 来源、可选 SHA-256、受限 ZIP 解压和原子目录替换。它们不修改系统 Chrome，不创建 Profile，不保存 Cookie，也不管理账号或扩展。

`remove` 必须显式传 `--yes`。`gc` 默认 dry-run，只处理超过最小年龄的 backend 临时/backup 目录；实际清理同时需要 `--apply --yes`。

## ChatStyle 交互

可恢复缺参通过 ChatStyle `CommandSchema` 处理：

- `-i` 强制当前子命令的缺参补问；
- `-I` 禁止补问，缺少 required 值时快速失败；
- `CHATARCH_AUTO_PROMPT=0/false/no/off` 关闭默认自动补问；
- CLI 参数和 prompt 返回值使用相同校验；
- 删除/清理不会通过默认确认 prompt 放宽，仍需要 `--yes`。

## Python API

消费方选择精确 backend module，不经过通用 Browser base：

```python
from chatup.chrome_for_testing import resolve as resolve_cft
from chatup.chromedriver import resolve as resolve_driver

browser = resolve_cft("145.0.7632.6")
driver = resolve_driver("145.0.7632.6")
print(browser.binary_path)
print(driver.binary_path)
```

ChatPost 当前只依赖 `chatup.chrome_for_testing`。它继续自己管理 isolated user-data-dir、Runner process、CDP/bridge、扩展、人工登录、账号映射和 publication ledger。
