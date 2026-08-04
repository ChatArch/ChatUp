# CLI Tree

ChatUp uses first-class top-level commands without forcing unlike browser artifacts and toolchains into one `browser` abstraction. Chrome for Testing, ChromeDriver, and Playwright own independent command sets, Python APIs, metadata, and storage roots.

## Top-Level Commands

```text
chatup
├── doctor              # Verify that ChatUp is callable
├── uv                  # Install uv and ~/.chatarch/venv
├── workspace           # Initialize a ChatArch workspace
├── nodejs              # Install nvm and default LTS Node.js
├── docker              # Check Docker and permissions
├── zsh                 # Configure zsh, plugins, and aliases
├── chrome-for-testing  # Manage Google Chrome for Testing browsers
├── chromedriver        # Manage ChromeDriver WebDriver servers
├── playwright          # Manage Playwright packages and Chromium browsers
├── frp                 # Install FRP Client/Server
├── gitea               # Install ChatTea-compatible Gitea
├── mysql               # Install ChatData-compatible MySQL
├── nginx               # Prepare user-level NGINX
├── crs                 # Install local Claude Relay Service plus Redis
├── cc-connect          # Install ChatArch CC Connect
├── claude              # Install/configure Claude Code
├── codex               # Install/configure Codex CLI
├── cursor-agent        # Install/configure Cursor Agent CLI
├── opencode            # Install/configure OpenCode
├── hermes              # Install Hermes Agent and optional WebUI
└── lark-cli            # Configure official lark-cli with ChatEnv
```

See [Command Reference](commands.md) for complete options.

## Cursor Agent

```text
chatup cursor-agent
├── --auth-json PATH
├── --auth-env PATH
├── --env-profile NAME
├── --save-profile NAME
├── --cli-config PATH
├── --agent-state PATH
├── --api-key-env NAME
├── --credential-store native|file-wrapper
├── --install-only
├── --verify / --no-verify
└── -i / -I
```

`cursor-agent` manages Cursor Agent CLI installation and login-state copying, and registers the ChatEnv `CursorAgent` config type. It never prints tokens in argv or output; `auth.json`, `cli-config.json`, and `agent-cli-state.json` are written with `0600` permissions. For migrated Linux file auth on macOS, use `--credential-store file-wrapper` to write a token-free wrapper.

Common migration form:

```bash
chatup cursor-agent --auth-json ./auth.json --cli-config ./cli-config.json --agent-state ./agent-cli-state.json --credential-store file-wrapper -I
chatup cursor-agent --env-profile work --credential-store file-wrapper -I
```

## Artifact Identity

| Backend | Actual artifact | Role |
| --- | --- | --- |
| `chrome-for-testing` | Google Chrome for Testing | Launchable browser with extension and CDP support |
| `chromedriver` | ChromeDriver | WebDriver protocol server; not a browser |
| `playwright` | Playwright package + Playwright Chromium | Pins package, revision, browser version, and executable path |

`Chrome for Testing` is Google's official distribution name. The `for-testing` suffix identifies the artifact; it does not expose a ChatUp `test` operation. None of the three backends has a `test` subcommand. Health checks are named `doctor`.

`chatup chromium` is intentionally unregistered. ChatUp will add an independent Chromium backend only after selecting and verifying a real Chromium source, revision contract, platform layout, and acceptance path.

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

`--version` and `--channel` are mutually exclusive for installation. Stable is the default when neither is given. Resolve-style operations require an exact four-component version; channels and old `chrome@...` / `cft@...` references are rejected.

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

The four install selectors are mutually exclusive. `--match-browser` reads `--version` from the supplied browser binary, resolves Google's build manifest first, and falls back to the milestone manifest; the browser and driver patch components need not match. `--match-cft-version` uses an exact CFT version directly. ChromeDriver is not involved in ChatPost's current extension/CDP Zhihu path.

```bash
chatup chromedriver install --channel stable -I
chatup chromedriver install --match-cft-version 145.0.7632.6 -I
chatup chromedriver install --match-browser /path/to/browser --output json -I
```

## Playwright

```text
chatup playwright
├── install [VERSION]
│   ├── --browser chromium
│   ├── --home PATH
│   ├── --force
│   ├── --doctor / --no-doctor
│   ├── --output text|json
│   └── -i / -I
├── path [VERSION] [--browser chromium] [--output text|json] [-i|-I]
└── doctor [VERSION] [--execute|--no-execute] [--output text|json] [-i|-I]
```

The Playwright backend accepts an exact three-component package version. `install` uses an available Node.js/npm runtime to install that package and download its declared Chromium revision into the same ChatArch-owned installation. `path` returns the executable resolved by Playwright itself. This backend creates no profile, launches no browser, and installs no ChromeDriver.

```bash
chatup nodejs -I
chatup playwright install 1.61.1 --output json -I
chatup playwright path 1.61.1 -I
chatup playwright doctor 1.61.1 --output json -I
```

## Independent Storage

```text
~/.chatarch/
├── chrome-for-testing/
│   └── <version>/<platform>/
│       ├── installation.json
│       └── <Google archive tree>/
├── chromedriver/
│   └── <version>/<platform>/
│       ├── installation.json
│       └── <Google archive tree>/
└── playwright/
    └── <playwright-version>/<browser>/
        ├── installation.json
        ├── package/
        └── browsers/
```

Chrome for Testing and ChromeDriver enforce official Google HTTPS provenance, optional SHA-256 verification, bounded ZIP extraction, and atomic directory replacement. Playwright uses npm package integrity and Playwright's browser manifest/download flow with the same atomic installation boundary. None modifies system Chrome, creates profiles, stores cookies, or manages accounts/extensions.

`remove` requires explicit `--yes`. `gc` defaults to dry-run and only targets backend temporary/backup directories older than the minimum age; deletion requires `--apply --yes`.

## ChatStyle Interaction

Recoverable missing inputs use ChatStyle `CommandSchema`:

- `-i` forces missing-value prompts for the current subcommand;
- `-I` disables prompts and fails fast when required values are absent;
- `CHATARCH_AUTO_PROMPT=0/false/no/off` disables automatic prompting;
- CLI and prompted values receive the same validation;
- destructive remove/gc paths still require `--yes` and are never relaxed by a default prompt.

## Python API

Consumers choose an exact backend module instead of a generic Browser base:

```python
from chatup.chrome_for_testing import resolve as resolve_cft
from chatup.chromedriver import resolve as resolve_driver
from chatup.playwright import resolve as resolve_playwright

browser = resolve_cft("145.0.7632.6")
driver = resolve_driver("145.0.7632.6")
playwright_browser = resolve_playwright("1.61.1", browser="chromium")
print(browser.binary_path)
print(driver.binary_path)
print(playwright_browser.binary_path)
```

ChatPost can select either a `chatup.chrome_for_testing` or `chatup.playwright` descriptor according to the proven task. It still owns isolated user-data directories, runner processes, CDP/bridge endpoints, extensions, manual login, account mapping, and the publication ledger.
