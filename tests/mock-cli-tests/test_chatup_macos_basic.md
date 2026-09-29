# macOS application selection test design

`chatup macos` offers exactly Snipaste, iTerm2 and Google Chrome, all checked by
default. It reuses the native desktop installer and only runs on macOS.

## Selection and execution

- On a macOS TTY, no explicit `--app` opens a ChatStyle checkbox with all three
  apps checked. Space toggles choices; Enter installs only the remaining choices.
- `--app snipaste` selects only Snipaste; repeated `--app` selects a subset and
  duplicate values install once. Explicit apps skip automatic prompts.
- `-i` forces selection, using explicit apps as the initial checked values when
  supplied. `-I`, disabled auto prompting, and non-TTY execution use the specified
  apps or all three defaults without prompting. Forced interaction without a TTY
  must fail before installation.
- Empty selection is a successful no-op. Ctrl-C cancels before any install.
- Reject unknown names and unsupported operating systems before downloading or
  prompting. An install failure stops with nonzero status and preserves earlier
  successful installations for a subsequent idempotent rerun.
- `--dry-run` without `-i` prints plans for the specified/default apps without
  prompting, downloads, subprocesses or filesystem writes.

```sh
chatup macos
chatup macos -I
chatup macos --app snipaste --app chrome
chatup macos --app snipaste -i
chatup macos --dry-run
```

## Snipaste installer

- Use the official current macOS DMG and verify its `com.Snipaste` bundle,
  version, executable and publisher signature before copying into Applications.
- Reuse all existing macOS install guarantees: staged copy, existing app reuse,
  non-writable system Applications fallback, cleanup and signature failure.
- Snipaste is macOS-only in this release; it must never fall through to a Chrome
  Windows/Linux installation plan.
- Preserve the existing standalone `chatup chrome` and `chatup iterm` commands.
- A normal install includes ChatStyle's TUI extra so checkbox selection is
  available without asking users to install another dependency manually.
