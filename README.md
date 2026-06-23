# chatup

ChatUp is the standalone ChatArch setup CLI. It is the first-level replacement for `chattool setup`: commands such as `chattool setup workspace` become `chatup workspace` while preserving the same interactive/non-interactive CLI conventions.

## Quick Start

```bash
chatup --help
chatup doctor
chatup uv
```

`chatup uv` installs `uv` through the official installer when needed, then creates the ChatArch Python environment with pip. Defaults are `--venv ~/.chatarch/venv` and `--python 3.12`; override them when a different runtime path or Python minor version is required.

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
