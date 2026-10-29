# WeType installation contract

`chatup wetype` installs the signed official macOS input method, using the
3.0.0 (build 670) ZIP advertised by the vendor site's InstallInfo manifest.
It does not add WeType to the `chatup macos` default selection.

- Darwin arm64 and x86_64 use the universal archive. Linux, Windows and other
  platforms fail before downloading, running a process or creating a cache.
- `--dry-run` prints the official ZIP and input-method destination without
  network, subprocess or filesystem writes.
- Search `/Library/Input Methods` and `~/Library/Input Methods`, verifying and
  reusing an existing bundle, including versions newer than the pinned download.
  Never install an input method in `/Applications` or overwrite an invalid one.
- Fresh installs prefer writable `/Library/Input Methods`, otherwise use the
  current user's input-method directory without sudo. Safely extract the ZIP,
  verify `com.tencent.inputmethod.wetype`, version, executable, minimum macOS,
  Tencent Team ID `88L2Q4487U`, and Gatekeeper notarization before staging/copy.
- Signature/notarization/version/copy failures exit nonzero, clean staging, and
  never report success. Reject traversal and escaping symlinks in the ZIP.
- Repeat execution verifies and reuses the app without downloads or upgrades.
- Success prints system input-source activation and Fn / Fn+Space voice shortcut
  guidance. It does not launch the app, select an input source, grant permissions,
  change shortcut preferences, or automatically record audio.

```sh
chatup wetype --help
chatup wetype --dry-run
chatup wetype
chatup wetype
chatup --tree
```
