from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from chatup.config import CursorAgentConfig, DiscourseAdminConfig, ZulipAdminConfig


ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_chatup_depends_on_chatenv_and_registers_cursor_agent_config_provider():
    data = _pyproject()

    assert data["project"]["requires-python"] == ">=3.10"
    assert "click>=8.0,<9.0" in data["project"]["dependencies"]
    assert "chatstyle>=0.2.0,<0.3.0" in data["project"]["dependencies"]
    assert "chatenv>=0.2.11,<0.3.0" in data["project"]["dependencies"]
    assert "python-dotenv>=1.0,<2.0" in data["project"]["dependencies"]
    entry_points = data["project"]["entry-points"]["chatenv.configs"]
    assert entry_points["cursor-agent"] == "chatup.config:CursorAgentConfig"
    assert entry_points["discourse"] == "chatup.config:DiscourseAdminConfig"
    assert entry_points["zulip"] == "chatup.config:ZulipAdminConfig"


def test_chatup_cursor_agent_config_schema_marks_tokens_sensitive():
    fields = CursorAgentConfig.get_fields()

    assert CursorAgentConfig.get_storage_name() == "CursorAgent"
    assert CursorAgentConfig._aliases == ["cursor-agent", "cursor_agent", "cursor"]
    assert fields["CURSOR_ACCESS_TOKEN"].env_key == "CURSOR_ACCESS_TOKEN"
    assert fields["CURSOR_ACCESS_TOKEN"].is_sensitive is True
    assert fields["CURSOR_REFRESH_TOKEN"].env_key == "CURSOR_REFRESH_TOKEN"
    assert fields["CURSOR_REFRESH_TOKEN"].is_sensitive is True
    assert fields["CURSOR_CREDENTIAL_STORE"].env_key == "CURSOR_CREDENTIAL_STORE"
    assert fields["CURSOR_CREDENTIAL_STORE"].default == "native"
    CursorAgentConfig.test()


def test_chatup_service_admin_config_schemas_mark_passwords_sensitive():
    discourse_fields = DiscourseAdminConfig.get_fields()
    zulip_fields = ZulipAdminConfig.get_fields()

    assert DiscourseAdminConfig.get_storage_name() == "Discourse"
    assert discourse_fields["DISCOURSE_ADMIN_PASSWORD"].is_sensitive is True
    assert ZulipAdminConfig.get_storage_name() == "Zulip"
    assert zulip_fields["ZULIP_ADMIN_PASSWORD"].is_sensitive is True
    assert "ZULIP_ADMIN_MAIL" in zulip_fields
    DiscourseAdminConfig.test()
    ZulipAdminConfig.test()


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
    assert "workspace/templates/default/zh/discussion/*.md" in package_data
    assert "workspace/templates/default/en/*.md" in package_data
    assert "workspace/templates/default/en/projects/*.md" in package_data
    assert "workspace/templates/default/en/discussion/*.md" in package_data


def test_project_metadata_points_to_chatup_docs_site():
    data = _pyproject()

    assert data["project"]["urls"]["Documentation"] == "https://arch.gh.wzhecnu.cn/ChatUp/"
    assert data["project"]["urls"]["Source"] == "https://github.com/ChatArch/ChatUp"
    assert "mkdocs-material>=9.5,<9.7" in data["project"]["optional-dependencies"]["docs"]
    assert "mkdocs-static-i18n>=1.2,<2.0" in data["project"]["optional-dependencies"]["docs"]
