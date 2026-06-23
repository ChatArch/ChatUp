# chatup

ChatUp is the standalone ChatArch setup CLI. It starts as the extraction target for `chattool setup` and will gradually receive the existing setup commands while preserving ChatTool's interactive/non-interactive CLI conventions.

## Quick Start

```bash
chatup --help
chatup doctor
```

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
