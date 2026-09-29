# Chrome / iTerm2 CLI test design

The new `chrome` command installs regular Google Chrome, separate from the
existing Chrome for Testing artifact backend. `iterm` installs iTerm2 on macOS.
These cases mock external downloads and system commands; no host app is installed.

## Plans and platform boundaries

- Prepare Darwin (arm64/x86_64), Windows, Linux x86_64 and unsupported OS/CPU cases.
- Chrome selects Google's universal macOS DMG, exact WinGet `Google.Chrome`, or
  the official stable DEB/RPM through apt/dnf/yum/zypper. iTerm2 selects its
  official stable ZIP on Darwin and rejects other systems before any side effect.
- `--dry-run` prints the plan, without downloads, subprocesses or directory writes.
- Linux without root or `--sudo` fails with the required command before download;
  `--yes` forwards package-manager agreement/noninteractive switches.

```sh
chatup chrome --dry-run
chatup chrome --dry-run --sudo --yes
chatup iterm --dry-run
```

## macOS installation and repeated execution

- Build temporary app fixtures with bundle ID, executable and version.
- Verify existing apps in `/Applications` or `~/Applications` before downloading.
- A fresh install downloads official HTTPS artifacts, mounts the DMG or safely
  extracts the ZIP, verifies the publisher signature and bundle, copies to a
  staging directory and moves the verified app into place.
- Prefer writable `/Applications`; otherwise use `~/Applications`, without sudo.
- Detach mounted images and remove temporary staging after success or failure.
- Never overwrite an existing invalid bundle. Repeated execution reuses a valid
  install without downloading, launching or modifying profiles/default apps.

```sh
chatup chrome
chatup chrome
chatup iterm
chatup iterm
```

## Errors and package-manager verification

- Exercise download, signature, copy, timeout and subprocess failures: exit
  nonzero, report the cause and never claim successful installation.
- Reject ZIP traversal and escaping symlinks before extraction.
- On Windows, use exact package selection and verify the matching WinGet record.
- On Linux, verify `google-chrome --version` before and after installation;
  reject Chromium/CFT output and unsupported architectures/package managers.
- Preserve independent CFT/ChromeDriver/Playwright groups in help and CLI trees.

```sh
chatup chrome --help
chatup iterm --help
chatup --tree
chatup --tree-brief
```
