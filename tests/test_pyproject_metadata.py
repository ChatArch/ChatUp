from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_chatup_reuses_chatenv_shared_configs_without_provider_entry_point():
    data = _pyproject()

    assert "chatstyle>=0.1.0,<0.2.0" in data["project"]["dependencies"]
    assert "chatenv>=0.2.0,<0.3.0" in data["project"]["dependencies"]
    assert "entry-points" not in data["project"] or "chatenv.configs" not in data["project"]["entry-points"]


def test_chatup_config_reexports_chatenv_shared_configs():
    from chatenv.configs import FeishuConfig as SharedFeishuConfig
    from chatenv.configs import OpenAIConfig as SharedOpenAIConfig
    from chatup.config import FeishuConfig, OpenAIConfig

    assert OpenAIConfig is SharedOpenAIConfig
    assert FeishuConfig is SharedFeishuConfig


def test_setup_package_data_includes_assets_and_workspace_templates():
    data = _pyproject()
    package_data = data["tool"]["setuptools"]["package-data"]["chatup.setup"]

    assert "assets/opencode_chatloop/commands/*.md" not in package_data
    assert "assets/opencode_chatloop/plugins/chatloop/*" not in package_data
    assert "workspace/templates/default/zh/*.md" in package_data
    assert "workspace/templates/default/zh/projects/*.md" in package_data
    assert "workspace/templates/default/en/*.md" in package_data
    assert "workspace/templates/default/en/projects/*.md" in package_data
