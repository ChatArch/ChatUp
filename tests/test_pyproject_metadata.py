from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_chatup_depends_on_chatenv_without_registering_config_provider():
    data = _pyproject()

    assert data["project"]["requires-python"] == ">=3.10"
    assert "chatstyle>=0.1.0,<0.2.0" in data["project"]["dependencies"]
    assert "chatenv>=0.2.0,<0.3.0" in data["project"]["dependencies"]
    assert "entry-points" not in data["project"] or "chatenv.configs" not in data["project"]["entry-points"]


def test_chatup_does_not_ship_a_config_package():
    assert not (ROOT / "src" / "chatup" / "config").exists()


def test_setup_modules_import_shared_configs_directly():
    for module in ["codex.py", "hermes.py", "lark_cli.py", "opencode.py"]:
        text = (ROOT / "src" / "chatup" / "setup" / module).read_text(encoding="utf-8")
        assert "from chatup.config" not in text
        assert "from chatenv.configs import" in text


def test_setup_package_data_includes_assets_and_workspace_templates():
    data = _pyproject()
    package_data = data["tool"]["setuptools"]["package-data"]["chatup.setup"]

    assert "assets/opencode_chatloop/commands/*.md" not in package_data
    assert "assets/opencode_chatloop/plugins/chatloop/*" not in package_data
    assert "workspace/templates/default/zh/*.md" in package_data
    assert "workspace/templates/default/zh/projects/*.md" in package_data
    assert "workspace/templates/default/en/*.md" in package_data
    assert "workspace/templates/default/en/projects/*.md" in package_data
