# Antigravity real acceptance

Use an authorized Apple Silicon or Intel Mac running macOS 13 or later.
Record existing `agy` and `Antigravity.app` installations before starting; do
not remove or replace them to exercise fresh installation.

1. Run `chatup antigravity --help`, each leaf's `--help` and `--dry-run`,
   `chatup --tree`, `chatup --tree-brief`, and `chatup all --list`.
   Confirm distinct `antigravity cli` and `antigravity desktop` actions.
   Dry runs must not download, create cache directories or run installers.
2. Run `chatup antigravity cli` twice. Read back the binary's `--version`;
   a valid existing binary must be reused. A custom `--install-dir` must be
   passed as one path argument, including spaces. Complete Google sign-in
   manually after installation when ready to use the CLI.
3. Run `chatup antigravity desktop` twice. Confirm `Antigravity.app`, bundle ID
   `com.google.antigravity`, Google Team `EQHXZ8M8AV`, notarization and version.
   Existing valid newer apps must be reused. A fresh app must be verified before
   atomic placement in writable `/Applications` or `~/Applications`.
4. Confirm mounted images are detached and installer staging is cleaned. No
   automatic Desktop launch, sign-in, startup item or permission change belongs
   to installer acceptance. `chatup macos` retains its current default apps.

```sh
chatup antigravity --help
chatup antigravity cli --dry-run
chatup antigravity desktop --dry-run
chatup antigravity cli
chatup antigravity cli
chatup antigravity desktop
chatup antigravity desktop
agy --version
chatup all --list
```
