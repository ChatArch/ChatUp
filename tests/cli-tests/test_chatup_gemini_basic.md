# Gemini real acceptance

Use an authorized Apple Silicon Mac running macOS 15 or later. Record existing
`gemini` and `Gemini.app` installations before testing; do not delete or replace
them to exercise fresh installation.

1. Run `chatup gemini --help`, each leaf's `--help` and `--dry-run`,
   `chatup --tree`, `chatup --tree-brief`, and `chatup all --list`.
   Confirm distinct `gemini cli` and `gemini desktop` actions. Dry runs must
   not download, create cache directories or execute installers/runtime probes.
2. Run `chatup gemini cli` twice. Confirm the official npm package
   `@google/gemini-cli`, Node.js 20+ and a successful `gemini --version` readback.
   The second invocation must reuse a valid existing installation. Complete
   Google account sign-in manually when ready to use the tool.
3. Run `chatup gemini desktop` twice. Confirm the official `Gemini.app`, bundle
   identity, Google Developer ID signature, Gatekeeper notarization and version.
   A fresh install must verify its staged copy before atomic placement into
   writable `/Applications` or `~/Applications`; valid newer apps are reused.
4. Confirm DMGs are detached and temporary installation staging is cleaned.
   No automatic app launch, sign-in, startup item or permission change belongs
   to installer acceptance. `chatup macos` keeps its current default apps.

```sh
chatup gemini cli --dry-run
chatup gemini desktop --dry-run
chatup gemini cli
chatup gemini cli
chatup gemini desktop
chatup gemini desktop
gemini --version
chatup all --list
```
