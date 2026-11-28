# Gemini installation contract

`chatup gemini cli` installs Google's official Gemini CLI npm package
`@google/gemini-cli`; `chatup gemini desktop` installs the official native
Gemini app advertised at `https://gemini.google/desktop/`.

- Each leaf supports an offline `--dry-run`, without downloads, subprocesses or
  installation-cache writes. Help/tree expose both leaves; `chatup all` filters
  them for host support. Installation and verification failures exit nonzero.
- CLI supports macOS/Linux/Windows, requires Node.js 20+ and installs through
  npm using ChatUp's shared runtime helpers. POSIX without suitable Node gives
  `chatup nodejs` guidance; Windows can bootstrap the existing managed runtime.
  Verify a valid existing CLI instead of upgrading it. Existing launchers must
  resolve to the official `@google/gemini-cli` package, including alternate npm
  or Homebrew prefixes; preserve and reject unrecognized same-name wrappers.
  Success requires a callable `gemini` launcher on the selected runtime PATH
  and a successful `gemini --version` readback. Preserve an installed package
  with a missing/unreachable launcher, fail with PATH/repair guidance and do
  not reinstall it automatically. Do not create API credentials, change
  provider configuration or sign in.
- Desktop supports macOS 15+ on Apple Silicon only. Use the official DMG
  endpoint `https://gemini.google/download/mac/`, not a third-party wrapper,
  browser shortcut or PWA. Reject unsupported hosts/architectures/OS versions
  before writes or download.
- Prefer writable `/Applications/Gemini.app`, falling back to
  `~/Applications/Gemini.app`. Verify bundle identity, executable, version,
  minimum macOS, Google Developer ID Team `EQHXZ8M8AV` signature and Gatekeeper
  notarization. The expected bundle ID is `com.google.GeminiMacOS`.
  Verify staging before atomic placement, then read back the installed app.
- Reuse verified existing apps, including newer versions. Preserve and reject
  invalid apps and broken symlinks. Download/signature/notarization/copy errors
  must clean staging and detach DMGs without overwriting existing apps; never
  recursively clean a still-mounted image.
- Do not launch Desktop, sign in, grant permissions, change startup items or
  add Gemini to `chatup macos` defaults. Antigravity commands remain available.

```sh
chatup gemini cli --help
chatup gemini cli --dry-run
chatup gemini desktop --help
chatup gemini desktop --dry-run
chatup --tree
chatup all --only 'gemini cli' --only 'gemini desktop' --dry-run -I
```
