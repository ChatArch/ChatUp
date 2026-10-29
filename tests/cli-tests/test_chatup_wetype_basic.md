# WeType real acceptance

Use an authorized Mac and record whether `/Library/Input Methods/WeType.app` or
`~/Library/Input Methods/WeType.app` already exists. Do not replace an existing
installation or treat a mock fresh install as a real first-install result.

1. Run installed `chatup wetype --help`, `--dry-run`, and `chatup --tree`.
   Confirm the official universal 3.0.0 ZIP and input-method destination.
2. Run `chatup wetype`, then repeat. Verify the bundle ID, Tencent signature,
   notarization and version. An existing valid installation must be reused.
3. For a fresh-install test, use an explicitly authorized clean user environment.
   Confirm the staged app is installed in Input Methods and no installer/cache
   residue remains. Do not alter the current user's app just to exercise this.
4. Manually add the input method in System Settings if necessary. Open WeType
   Settings > Voice Input and read the configured shortcuts. Do not grant system
   permissions or start recording as part of unattended verification.

```sh
chatup wetype --help
chatup wetype --dry-run
chatup wetype
chatup wetype
chatup --tree
```
