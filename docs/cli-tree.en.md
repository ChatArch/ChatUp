# CLI Tree

ChatUp uses flat, first-class installer commands. Each top-level command owns one machine environment, toolchain, or local service; there is no extra `setup` or `browser` layer.

## Top-Level Commands

```text
chatup
├── doctor       # Verify that ChatUp is callable
├── uv           # Install uv and ~/.chatarch/venv
├── workspace    # Initialize a ChatArch workspace
├── nodejs       # Install nvm and default LTS Node.js
├── docker       # Check Docker and permissions
├── zsh          # Configure zsh, plugins, and aliases
├── chrome       # Install ChatArch-internal Chrome for Testing
├── frp          # Install FRP Client/Server
├── gitea        # Install ChatTea-compatible Gitea
├── mysql        # Install ChatData-compatible MySQL
├── nginx        # Prepare user-level NGINX
├── crs          # Install local Claude Relay Service plus Redis
├── cc-connect   # Install ChatArch CC Connect
├── claude       # Install/configure Claude Code
├── codex        # Install/configure Codex CLI
├── opencode     # Install/configure OpenCode
├── hermes       # Install Hermes Agent and optional WebUI
└── lark-cli     # Configure official lark-cli with ChatEnv
```

See [Command Reference](commands.md) for complete options.

## Why Chrome Is Independent

Chrome is a machine dependency at the same level as `uv`, `nodejs`, and `docker`. ChatUp installs it; consumers resolve the result.

Do not design:

```text
chatup browser install chrome
chatpost browser install chrome
```

Use one command instead:

```bash
chatup chrome
```

ChatPost, ChatBlog automation, and future packages can reuse one environment without coupling installation to a product-specific Browser Runner model.

## `chatup chrome` Contract

```text
chatup chrome
├── --version VERSION          # stable/beta/dev/canary or exact version
├── --home PATH                # default ~/.chatarch/chrome
├── --platform PLATFORM        # auto-detected by default
├── --sha256 HEX               # optional expected archive digest
├── --force                    # atomically replace the same version
├── --doctor / --no-doctor     # run the version probe or not
├── --output text|json         # human or machine output
└── -i / -I                    # ChatStyle interaction policy
```

Default layout:

```text
~/.chatarch/chrome/
└── chrome-for-testing/
    └── <version>/
        └── <platform>/
            ├── runtime.json
            └── <vendor archive tree>/
```

The command:

- resolves a channel or exact version from the official Chrome for Testing manifest;
- supports `mac-arm64`, `mac-x64`, `linux64`, and `win64`;
- downloads into staging and checks HTTPS provenance, optional SHA-256, and ZIP path safety;
- atomically switches directories without destroying a working installation first;
- never modifies system Chrome;
- never installs into `~/.local/bin`;
- requires no Docker;
- creates no browser profile, extension, or cookie state.

## JSON Output

`--output json` is the stable downstream boundary:

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

Machines must not scrape colored text or logs to find the executable.

## Python API

Python consumers should import the API rather than shell out:

```python
from chatup.chrome import ensure_chrome, resolve_chrome

runtime = ensure_chrome(version="<tested-version>")
print(runtime.binary_path)
```

`ensure_chrome` may install a missing exact version. `resolve_chrome` reads existing `runtime.json` without a network write.

## ChatPost Boundary

ChatUp returns:

```text
binary_path
version
platform
runtime root
provenance/digest
health status
```

ChatPost still owns:

```text
isolated user-data-dir
runner process / port / lock
extension and bridge
manual login checkpoint
platform account mapping
publication ledger
```

Chrome installation is no longer part of the ChatPost CLI.
