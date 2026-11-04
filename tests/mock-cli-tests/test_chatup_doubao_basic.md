# Doubao installation contract

`chatup doubao` installs official Doubao 2.34.6 on macOS 12 or later, using
the architecture-specific DMGs advertised by the official settings API:
`https://www.doubao.com/service/settings/v3/?device_platform=web&brand=doubao&aid=582465`.
The release is pinned, so planning requires no network request.

- Darwin arm64/aarch64 selects the Arm64 DMG; x86_64/amd64 selects X64.
  Unsupported platforms, architectures and macOS versions fail before writes,
  network requests or subprocesses. Do not add Doubao to `chatup macos` defaults.
- `--dry-run` prints the official DMG URL and native application destination,
  without network requests, cache creation or subprocesses.
- Reuse verified `/Applications/Doubao.app` or `~/Applications/Doubao.app`,
  including a version newer than the pinned download. Do not overwrite invalid
  existing bundles or broken symlinks, shadow an invalid system app, or upgrade.
- Fresh installs prefer writable `/Applications`, falling back to
  `~/Applications` without sudo. Verify bundle ID `com.bot.pc.doubao`, version,
  executable, minimum macOS, Developer ID Team `96L78H6LMH` and Gatekeeper
  notarization before staging and atomic placement; verify the installed bundle.
- Download/version/signature/notarization/copy failures must exit nonzero,
  preserve an existing app, detach mounted images and clean cache/staging.
  A still-mounted image must never be recursively removed.
- Python callers use `plan_desktop_install("doubao")` and
  `setup_desktop_app("doubao", dry_run=False)` from `chatup.setup.desktop`.
- Do not launch Doubao, log in, change permissions, enable startup items or
  write application login state. Native application data remains app-owned.

```sh
chatup doubao --help
chatup doubao --dry-run
chatup doubao
chatup doubao
chatup --tree
```
