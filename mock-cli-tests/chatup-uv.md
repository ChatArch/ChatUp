# chatup uv mock CLI test

Mock/unit coverage should avoid running the real official installer or mutating `~/.chatarch/venv`.

## Cases

- `chatup uv --help` exposes the documented defaults.
- when `uv` is already discoverable, setup uses the discovered binary.
- when `uv` is missing, setup calls the official installer wrapper.
- default setup uses `~/.chatarch/venv` and Python `3.12`.
- custom `--venv`, custom `--python`, and `--force` are passed through to the implementation.
- forced recreation uses `uv venv --clear --force`.
- existing same-version venv repair uses `uv venv --allow-existing`.
- the venv creation path uses `uv venv --seed` so `pip` is available.
