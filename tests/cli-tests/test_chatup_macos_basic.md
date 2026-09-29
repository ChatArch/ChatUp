# macOS setup real acceptance

## Preparation

Use the authorized Apple Silicon Mac. Chrome and iTerm2 were installed through
ChatUp 0.2.17; Snipaste is initially absent. Use a project-local venv, and keep
test artifacts under the task's playground.

## Execution and expected result

1. Invoke `chatup macos -i --dry-run` in a real PTY. Check that exactly Snipaste,
   iTerm2 and Chrome are selected by default; Enter previews all three.
2. Invoke the same command again, toggle off two apps and verify only the selected
   app appears in the plan. Empty selection must not install anything.
3. Run `chatup macos -I` to install the default group. Snipaste is downloaded from
   its official source, validated and installed; Chrome/iTerm2 are verified and reused.
4. Run `chatup macos --app snipaste -I` again. Verify the installed bundle/version
   and no second download. Check Developer ID/notarization and open Snipaste.
5. Verify the running app/UI. If macOS requires user screen-recording consent for
   capture, record that accurately instead of claiming capture succeeded.
6. After publication, upgrade the normal ChatUp environment from PyPI and repeat
   version/help/tree checks plus the installed-app readback.

```sh
chatup macos -i --dry-run
chatup macos -I
chatup macos --app snipaste -I
spctl --assess --type execute --verbose=2 /Applications/Snipaste.app
open -a /Applications/Snipaste.app
```
