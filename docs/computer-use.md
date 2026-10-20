# Linux Computer Use

`chatup computer-use` 为同一普通用户的 X11 桌面准备受管 `cua-driver` 执行入口。当前安装器仅支持 Debian/Ubuntu Linux x86_64 的 X11 会话；未声称支持 Wayland、其他发行版或远程桌面自动路由。

## 先预览，再显式应用

```bash
chatup computer-use
chatup computer-use --sudo --dry-run
chatup computer-use --display :20 --xauthority "$XAUTHORITY"
chatup computer-use --state "$CHATARCH_HOME/computer-use/run/desktop.env.json"
chatup computer-use --sudo
```

裸命令和 `--sudo --dry-run` 只读取本机系统、X11 socket 和同用户状态，输出 JSON 计划；不探测 sudo、不创建目录、不下载、不启动进程、不读取模型凭据。只有单独使用 `--sudo` 才会应用。`--display` 必须与 `--xauthority` 同传；`--state` 选择同用户桌面元数据，与前两者互斥。`--home` 可显式指定受管根目录，默认取有效 ChatEnv/`CHATARCH_HOME`。

计划包含目标 hostname/UID、桌面选择、拟安装包、Chrome/driver 复用、入口路径、安全与能耗影响。已有同用户 X11 状态或当前 X11 会话优先复用；显式选择能连接的同用户桌面时，只附着使用，不改写、重启或启用原服务。没有可复用桌面时才规划独立的 Xfce/TigerVNC 用户会话。该会话使用密码认证，仅监听 loopback VNC；不安装 display manager、不升级 GPU/系统、不改防火墙或公网端口。受管桌面会持续消耗资源，并在运行期间关闭屏幕空白与 DPMS；通过其自有 user service 正常启停。

## 受管运行态与入口

应用后，ChatUp 在有效 ChatArch home 的 `computer-use/chatup-<version>/` 下放置专用 venv、官方 PyPI `cua-driver==0.36.0`、私有目标元数据及独立的 `mcp`、`chrome`、`terminal`、`status` 入口。若同用户现有专用 Computer Use venv 中的 driver 已核实兼容，命名空间仅链接复用该 venv，不改动原运行态。新建桌面另有自有 `desktop` 入口和 user service。JSON 返回实际绝对路径；可先运行返回的 `entrypoints.status`，检查目标、显示器、入口和是否就绪。状态文件和 VNC 凭据限当前用户读取，入口启动前复核 hostname、UID、Xauthority 与活动 X11 socket；失效时拒绝执行，不退回调用者的屏幕。

已安装的普通 Google Chrome 会验证后复用，不自动升级或启动。若缺失，应用阶段沿用 `setup_desktop_app('chrome')` 安装契约。`chrome` 侧入口仅在明确调用时用当前用户默认 profile 开窗口；不使用 Chrome for Testing、自定义 user-data-dir，不复制 Cookie/密码，也不自动登录或接受默认浏览器/遥测选项。MCP 入口使用受管运行态下私有的 driver 专用 HOME，将 driver 的 home 状态导向该目录；Chrome 和 terminal 入口仍使用普通用户 HOME，不迁移现有全局 driver 状态。driver 子进程只接收限定环境，模型和安装器密钥不传入。厂商实际状态路径仍需现场验收。

远端 Agent 若需要 MCP，应单独配置执行端的明确 SSH 目标和返回的绝对 `entrypoints.mcp` 路径，例如将目标主机与入口路径填入其 MCP 配置。ChatUp 不修改 Hermes 或其他 Agent 配置，也不设置全局 `HERMES_CUA_DRIVER_CMD` 或 terminal backend。**ChatUp 安装不能修复 Hermes 按话题 SSH 绑定时默认截图可能落到控制端的问题**；该路由缺口属于 Hermes，必须单独修复并验收。安装器与 driver 提供原生截图/输入执行条件；图像理解由 Agent/模型承担，DOM 访问是另一种授权能力，已登录状态来自同一用户现有 Chrome profile，四者不能互相替代。
