# chatup

ChatUp is the standalone ChatArch setup CLI. It is the first-level replacement for `chattool setup`: commands such as `chattool setup workspace` become `chatup workspace` while preserving the same interactive/non-interactive CLI conventions.

## Quick Start

```bash
chatup --help
chatup doctor
chatup uv
chatup gitea --install-dir ~/.chatarch/bin --force
chatup crs --install-dir ~/.chatarch/crs/local --port 12392 --redis-port 6379
```

`chatup uv` installs `uv` through the official installer when needed, then creates the ChatArch Python environment with pip. Defaults are `--venv ~/.chatarch/venv` and `--python 3.12`; override them when a different runtime path or Python minor version is required.

`chatup gitea` installs the ChatArch-maintained Gitea binary from `ChatArch/gitea` GitHub Release assets. It defaults to version `1.0.0`, repository `ChatArch/gitea`, and install directory `~/.chatarch/bin`.

`chatup crs` installs the canonical `@chatarch/claude-relay-service` npm package, prepares a local Redis component with task/app-local config, writes local secrets without printing them, builds the admin SPA, starts CRS, and runs a local smoke check. It does not register Redis as a Homebrew/system service.

## Development

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
```

## Layout

- `src/chatup/`: package source code
- `tests/`: package tests
- `cli-tests/`: real CLI tests, doc-first
- `mock-cli-tests/`: mock/fake CLI tests, doc-first
- `docs/`: long-lived project docs

## Release

Release is tag-driven. A `vX.Y.Z` tag must match `src/chatup/__init__.py::__version__`; the publish workflow builds and publishes to PyPI through Trusted Publishing/OIDC when the PyPI project is configured for `ChatArch/ChatUp`, workflow `.github/workflows/publish.yml`, environment `pypi`.
