# Chrome / Snipaste / iTerm2 real acceptance

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

## Windows execution and expected results

Use an authorized Windows desktop with WinGet available. Record whether Chrome
and Snipaste already exist, then run the following commands when their system
installation is explicitly requested.

1. Run both dry runs and confirm the exact WinGet IDs `Google.Chrome.EXE` (current
   user scope) and `liule.Snipaste`, with no installer process started.
2. Run `chatup chrome --yes` and `chatup snipaste --yes`. Confirm that each
   command checks the exact package ID before and after installation, then
   reports verified success. Chrome must also verify its installed executable's
   Google LLC Authenticode signature, product identity and version.
3. Repeat both commands and confirm already-installed output without upgrades.
4. Start both installed applications manually and confirm they are available;
   the CLI must not launch them, change Chrome defaults, or change Snipaste
   preferences.

```powershell
chatup --version
chatup chrome --dry-run
chatup snipaste --dry-run
chatup chrome --yes
chatup snipaste --yes
chatup chrome --yes
chatup snipaste --yes
```

Linux installation routes remain covered by mock tests in CI. A real Linux
installer result must be reported separately from that coverage.
