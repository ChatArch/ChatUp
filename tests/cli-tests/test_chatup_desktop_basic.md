# Chrome / iTerm2 real acceptance

## Initial environment

Use an authorized desktop machine with working network access. Record whether
Chrome/iTerm2 already exist. Run real installation only when explicitly requested.
For this release the user requests both apps installed on their Apple Silicon Mac,
which has neither app nor Homebrew.

## Execution and expected results

1. Run both `--help` and `--dry-run` commands from the built/installed ChatUp.
   Confirm official artifact URLs, native app destinations and no downloads.
2. Run `chatup chrome` and `chatup iterm`. Confirm installed app bundle paths,
   versions, expected bundle IDs and valid Developer ID signatures.
3. Repeat each command. Confirm already-installed output without a new download.
4. Open each app and confirm its process/UI is available. Do not change default
   browser/terminal, user profiles, login state or preferences as part of the CLI.
5. Following publication, upgrade the normal ChatUp installation to the exact
   released version and repeat the installed-app readbacks.

```sh
chatup --version
chatup chrome --dry-run
chatup iterm --dry-run
chatup chrome
chatup iterm
chatup chrome
chatup iterm
open -a 'Google Chrome'
open -a iTerm
```

Windows/Linux installation routes are covered by mock tests in CI. A real
Windows/Linux installer result must be reported separately from that coverage.
