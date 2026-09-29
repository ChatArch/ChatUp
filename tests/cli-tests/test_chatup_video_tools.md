# Video tools real acceptance

1. Preserve the previously verified `/Applications/Blender.app` and the handoff
   Remotion project; record its source/lockfile hashes before and after.
2. Run `chatup macos --app blender -I`: verify and reuse Blender 5.2.2, with no
   new download or overwrite. Verify background startup and the Python API.
3. Exercise the real macOS menu in dry-run: four defaults on Apple Silicon.
4. Run `chatup remotion` into a new task-local project. Exercise directory
   selection through a real terminal prompt in dry-run. Verify npm's installed
   dependency versions and safe repeated execution.
5. Render the Welcome composition using the existing Chrome to a 3-second,
   1280x720 MP4, inspect a frame, and record the process. Do not leave Studio
   running. Do not grant additional global npm script permissions.
6. After publishing, clean-install the PyPI version, verify CLI help/tree and
   bundled templates, upgrade the normal ChatUp environment and read back the
   real Blender and managed Remotion project.

Only Apple Silicon macOS is tested end-to-end here. Python mocks cover other
platform selection and failure handling; they do not establish native installs
or renders on those platforms. The already-installed Blender is not replaced
solely to rerun its initial-install path.
