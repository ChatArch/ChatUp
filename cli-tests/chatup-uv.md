# chatup uv CLI test

Real CLI smoke coverage for the ChatArch Python environment installer.

## Help

```bash
chatup uv --help
```

Expected:

- command exits successfully
- help shows `--venv` / `--venv-path`
- help shows `--python` / `--python-version`
- default venv is `~/.chatarch/venv`
- default Python version is `3.12`
- `--force` is available for explicit recreation

## Task-local install smoke

Use a task-local target instead of mutating the default global ChatArch venv:

```bash
chatup uv --venv ./playground/uv-smoke-venv --python 3.12
./playground/uv-smoke-venv/bin/python -m pip --version
```

Expected:

- `uv` is discovered or installed by the official installer
- Python `3.12` is installed through `uv`
- the venv is created with seed packages
- `python -m pip --version` succeeds after creation
