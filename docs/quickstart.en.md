# Quick Start

## Recommended Paths

<div class="grid cards" markdown>

- **Base Runtime**

    Install ChatUp, then run `chatup doctor` and `chatup uv` to verify the CLI and Python runtime; install the exact Chrome for Testing backend only when browser automation is needed.

- **Workspace**

    Use `chatup workspace default ~/Playground` to initialize the ChatArch collaboration layout.

- **Local Services**

    Prepare `gitea`, `mysql`, `nginx`, and `crs` as needed; defaults stay under `~/.chatarch/...`.

</div>

## Install

For source development or local validation, use an editable install:

```bash
python -m pip install -e .
chatup --version
chatup doctor
```

In the default ChatArch runtime, ChatUp is often installed into `~/.chatarch/venv`:

```bash
~/.chatarch/venv/bin/python -m pip install -e .
~/.chatarch/venv/bin/chatup --help
```

## Prepare the Python Runtime

```bash
chatup uv
```

Default behavior:

- Install or reuse `uv`.
- Create `~/.chatarch/venv`.
- Use Python 3.12 by default.

To customize the target:

```bash
chatup uv --venv ~/.chatarch/venv --python-version 3.12
```

## Install the Chrome for Testing Browser

```bash
chatup chrome-for-testing install --channel stable -I
```

This installs Google Chrome for Testing under `~/.chatarch/chrome-for-testing` without modifying system Chrome. Use JSON when handing the result to another program:

```bash
chatup chrome-for-testing install --version 145.0.7632.6 --output json -I
```

Only Selenium/WebDriver consumers need the independent ChromeDriver backend:

```bash
chatup chromedriver install --match-cft-version 145.0.7632.6 -I
```

See [CLI Tree](cli-tree.md) for all options and the Python API.

## Initialize a Workspace

```bash
chatup workspace default ~/Playground
```

This creates the base ChatArch workspace structure:

```text
AGENTS.md
projects/
archive/
core/
skills/
public/
.trash/
```

## Install Local Services

Install ChatArch Gitea:

```bash
chatup gitea --force
chatup gitea --init --service --base-url http://127.0.0.1:3000
```

Prepare a ChatData-compatible MySQL runtime:

```bash
chatup mysql
chatup mysql --start --smoke
```

Prepare user-level NGINX:

```bash
chatup nginx
```

Generate an NGINX reverse-proxy config:

```bash
chatup nginx proxy-pass ./gitea-local.conf \
  --set SERVER_NAME=gitea.local.example.invalid \
  --set PROXY_PASS=http://127.0.0.1:3000
```

Install a local Claude Relay Service:

```bash
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

`chatup crs` prepares the local Redis component and CRS configuration. The default smoke check expects the service to start. To prepare files without starting the service, pass both flags:

```bash
chatup crs --no-start --no-smoke
```

## Interactive Mode

ChatUp uses the shared interaction convention:

- `-i`: force prompts.
- `-I`: disable prompts, suitable for CI, scripts, and automation.
- `CHATARCH_AUTO_PROMPT=0/false/no/off`: disable automatic prompts.
- Commands may prompt for recoverable missing values; unrecoverable missing values should fail fast.
