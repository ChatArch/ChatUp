# Doubao real acceptance

Use an authorized Mac running macOS 12 or later. Record whether
`/Applications/Doubao.app` or `~/Applications/Doubao.app` already exists.
Never move or replace an existing installation just to exercise fresh install.

1. Run installed `chatup doubao --help`, `chatup doubao --dry-run`, and
   `chatup --tree`. Confirm the official 2.34.6 Arm64 or X64 DMG and native
   application destination. Dry-run must not download or write installer state.
2. Run `chatup doubao`, then repeat. Confirm the returned bundle version,
   `com.bot.pc.doubao`, Developer ID Team `96L78H6LMH`, and Gatekeeper
   notarization. A valid existing app, including a newer one, must be reused.
3. Fresh installation requires an explicitly authorized clean environment.
   Confirm signature/version verification before atomic placement, followed by
   readback, image detach and cache/staging cleanup.
4. Do not launch, log in, grant permissions or enable background startup during
   installer acceptance. `chatup macos` retains its existing default selection.

```sh
chatup doubao --help
chatup doubao --dry-run
chatup doubao
chatup doubao
chatup --tree
```
