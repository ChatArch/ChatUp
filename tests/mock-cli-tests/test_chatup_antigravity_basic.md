# Antigravity installation contract

`chatup antigravity cli` installs the official Google Antigravity terminal
client (`agy`); `chatup antigravity desktop` installs Antigravity App, the
separate Desktop surface, rather than the standalone Antigravity IDE.

- Each action supports an offline `--dry-run`: no network, cache writes or
  subprocesses. Help/tree expose both leaves; `chatup all` filters them for
  the host platform. Installation failures exit nonzero.
- CLI supports macOS/Linux/Windows x64/arm64. It uses the official
  `https://antigravity.google/cli/install.sh` bootstrapper on macOS/Linux,
  defaulting to `~/.local/bin/agy`; Windows uses the official `install.ps1`
  through PowerShell and defaults to `%LOCALAPPDATA%\agy\bin\agy.exe`. It delegates release selection, SHA512 verification and
  shell setup to Google's installer. `--install-dir PATH` chooses another
  directory. A verified existing binary is reused, including one not on PATH;
  an invalid existing binary is rejected. Success requires `agy --version`.
- Desktop supports macOS 13+ Apple Silicon and Intel. It uses pinned official
  App 2.36.0 DMGs, selecting `darwin-arm` or `darwin-x64` by architecture.
  Unsupported hosts fail before download or writes.
- Prefer writable `/Applications`, falling back to `~/Applications`. Reuse
  verified existing apps, including newer versions. Preserve and reject
  invalid bundles or broken symlinks; never overwrite or bypass an invalid
  system app by installing a user copy.
- Verify bundle ID `com.google.antigravity`, executable, version, minimum
  macOS, Google Developer ID Team `EQHXZ8M8AV` and Gatekeeper notarization.
  Verify a staged copy before atomic placement and read back the result.
  Version/signature/notarization/download/copy failures must clean staging and
  detach mounted images. Never recursively remove a still-mounted image.
- Do not launch the Desktop app, log in, change startup/permissions or modify
  other Agent configuration. Do not add Antigravity to `chatup macos` defaults.

```sh
chatup antigravity cli --help
chatup antigravity cli --dry-run --install-dir '/path with spaces/bin'
chatup antigravity desktop --help
chatup antigravity desktop --dry-run
chatup --tree
chatup all --only 'antigravity cli' --only 'antigravity desktop' --dry-run -I
```
