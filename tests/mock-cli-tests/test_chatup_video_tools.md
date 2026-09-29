# Blender and Remotion CLI test design

## Blender

- `chatup macos` on Apple Silicon adds Blender to the checked defaults; Intel
  keeps the existing three apps. Explicit Blender on Intel fails before changes.
- `chatup macos --app blender` uses the official pinned 5.2.2 arm64 DMG and
  SHA-256, bundle ID and Developer Team. Existing installations are verified and
  reused without downloads or upgrades.
- Dry-run does not download or execute. A checksum mismatch fails before mount;
  a wrong downloaded version, signature, notarization or copy failure cannot
  claim success. Mounted images detach and staging is cleaned on failure.
- Keep fake bundles under `.noindex` and remove them after each test.

## Remotion

- `chatup remotion PROJECT_DIR` initializes a local Remotion 4.0.530 project with
  pinned React versions and the shipped lockfile. Node >=18.12 and npm >=9 are
  required and checked before writes. Dependencies install with npm ci,
  lifecycle scripts disabled and platform optional packages included.
- Missing directory prompts on a TTY; `-I`, no TTY and disabled prompts require
  an explicit directory. `-i` without a TTY fails before writes. Cancellation
  does not install. Explicit directories skip automatic prompting.
- Dry-run is a read-only plan: no runtime processes, downloads or directory
  writes. It reports the target, pinned versions and browser strategy.
- Refuse existing unrelated directories, files or a symlink target. A managed
  project is recognized by a marker, then dependency versions are verified;
  repeated runs do not reinstall or overwrite user source files.
- Install into a hidden sibling staging directory, verify versions, write the
  ownership marker and rename only after success. npm failure or a destination
  appearing during install leaves user data untouched and cleans staging.
- Detect an existing Chrome or validate an explicit `--browser-executable`.
  Initialization does not download a browser. Missing Chrome reports how to
  install it before rendering; dependency installation can still succeed.
- Do not launch Studio, render video, install global npm packages, change Node
  or grant broad npm lifecycle-script permissions as part of initialization.

```sh
chatup macos --app blender --dry-run
chatup remotion ./my-video --dry-run -I
chatup remotion ./my-video -I
chatup remotion ./my-video -I
```
