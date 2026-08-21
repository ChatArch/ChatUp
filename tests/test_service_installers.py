from __future__ import annotations

from click.testing import CliRunner
from chatenv.paths import get_paths
from chatenv.store import EnvStore

from chatup.cli import main
from chatup.config import DiscourseAdminConfig, ZulipAdminConfig
from chatup.setup.discourse import setup_discourse
from chatup.setup.service_credentials import load_chatenv_values
from chatup.setup.zulip import setup_zulip


def test_discourse_and_zulip_help_expose_chatenv_options():
    for command in ["discourse", "zulip"]:
        result = CliRunner().invoke(main, [command, "--help"])
        assert result.exit_code == 0, result.output
        assert "-e, --env" in result.output
        assert "--env-profile" in result.output
        assert "--write-admin-env" in result.output


def test_discourse_admin_config_schema_marks_password_sensitive():
    fields = DiscourseAdminConfig.get_fields()
    assert DiscourseAdminConfig.get_storage_name() == "Discourse"
    assert fields["DISCOURSE_ADMIN_USERNAME"].env_key == "DISCOURSE_ADMIN_USERNAME"
    assert fields["DISCOURSE_ADMIN_EMAIL"].env_key == "DISCOURSE_ADMIN_EMAIL"
    assert fields["DISCOURSE_ADMIN_PASSWORD"].is_sensitive is True
    DiscourseAdminConfig.test()


def test_zulip_admin_config_schema_supports_email_and_mail_alias():
    fields = ZulipAdminConfig.get_fields()
    assert ZulipAdminConfig.get_storage_name() == "Zulip"
    assert fields["ZULIP_ADMIN_USERNAME"].env_key == "ZULIP_ADMIN_USERNAME"
    assert fields["ZULIP_ADMIN_EMAIL"].env_key == "ZULIP_ADMIN_EMAIL"
    assert fields["ZULIP_ADMIN_MAIL"].env_key == "ZULIP_ADMIN_MAIL"
    assert fields["ZULIP_ADMIN_PASSWORD"].is_sensitive is True
    ZulipAdminConfig.test()


def test_explicit_chatenv_profile_isolated_from_process_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch"))
    monkeypatch.setenv("DISCOURSE_ADMIN_USERNAME", "process-admin")
    monkeypatch.setenv("DISCOURSE_ADMIN_EMAIL", "process@example.com")
    monkeypatch.setenv("DISCOURSE_ADMIN_PASSWORD", "process-password")
    EnvStore(get_paths().envs_dir).save_profile(
        DiscourseAdminConfig,
        "selected",
        {
            "DISCOURSE_ADMIN_USERNAME": "profile-admin",
            "DISCOURSE_ADMIN_PASSWORD": "profile-password",
        },
    )

    values, source = load_chatenv_values(DiscourseAdminConfig, env_profile="selected")

    assert source == "ChatEnv profile selected"
    assert values["DISCOURSE_ADMIN_USERNAME"] == "profile-admin"
    assert values["DISCOURSE_ADMIN_PASSWORD"] == "profile-password"
    assert "DISCOURSE_ADMIN_EMAIL" not in values


def test_process_credentials_are_used_without_explicit_source(monkeypatch):
    monkeypatch.setenv("DISCOURSE_ADMIN_USERNAME", "process-admin")
    monkeypatch.setenv("DISCOURSE_ADMIN_EMAIL", "process@example.com")
    monkeypatch.setenv("DISCOURSE_ADMIN_PASSWORD", "process-password")

    values, source = load_chatenv_values(DiscourseAdminConfig)

    assert source == "environment"
    assert values == {
        "DISCOURSE_ADMIN_USERNAME": "process-admin",
        "DISCOURSE_ADMIN_EMAIL": "process@example.com",
        "DISCOURSE_ADMIN_PASSWORD": "process-password",
    }


def test_discourse_setup_writes_admin_env_and_chatarc_internal_app_yml(tmp_path):
    env = tmp_path / "discourse.env"
    env.write_text(
        "DISCOURSE_ADMIN_USERNAME=admin\n"
        "DISCOURSE_ADMIN_EMAIL=admin@example.com\n"
        "DISCOURSE_ADMIN_PASSWORD=secret-password\n",
        encoding="utf-8",
    )
    home = tmp_path / "discourse"

    result = setup_discourse(home=home, env_ref=env, clone=False, interactive=False)

    admin_env = home / "secrets" / "admin.env"
    app_yml = home / "docker" / "containers" / "app.yml"
    assert result["admin_env"] == str(admin_env)
    assert admin_env.stat().st_mode & 0o777 == 0o600
    assert "DISCOURSE_ADMIN_PASSWORD=secret-password" in admin_env.read_text(encoding="utf-8")
    text = app_yml.read_text(encoding="utf-8")
    assert f"host: {home / 'shared' / 'standalone'}" in text
    assert "127.0.0.1:3088:80" in text
    assert "/var/discourse" not in text


def test_zulip_setup_writes_compose_with_bind_mounts_and_hidden_admin_password(tmp_path):
    env = tmp_path / "zulip.env"
    env.write_text(
        "ZULIP_ADMIN_USERNAME=admin\n"
        "ZULIP_ADMIN_EMAIL=admin@example.com\n"
        "ZULIP_ADMIN_PASSWORD=secret-password\n",
        encoding="utf-8",
    )
    home = tmp_path / "zulip"

    result = setup_zulip(home=home, env_ref=env, port=3099, start=False, pull=False, interactive=False)

    admin_env = home / "secrets" / "admin.env"
    compose = home / "compose" / "compose.yaml"
    assert result["admin_env"] == str(admin_env)
    assert admin_env.stat().st_mode & 0o777 == 0o600
    assert "ZULIP_ADMIN_PASSWORD=secret-password" in admin_env.read_text(encoding="utf-8")
    text = compose.read_text(encoding="utf-8")
    assert "127.0.0.1:3099:80" in text
    assert 'user: "0:0"' in text
    assert "chown memcache:memcache" in text
    assert "exec memcached -S -u memcache" in text
    assert str(home / "data" / "postgresql-14") in text
    assert str(home / "data" / "zulip") in text
    assert "SETTING_ZULIP_ADMINISTRATOR: \"admin@example.com\"" in text
    assert "secret-password" not in text
    for name in ["postgres_password", "memcached_password", "rabbitmq_password", "redis_password", "secret_key", "email_password"]:
        path = home / "secrets" / name
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o600


def test_zulip_setup_accepts_admin_mail_alias(tmp_path):
    env = tmp_path / "zulip.env"
    env.write_text(
        "ZULIP_ADMIN_USERNAME=admin\n"
        "ZULIP_ADMIN_MAIL=admin@example.com\n"
        "ZULIP_ADMIN_PASSWORD=secret-password\n",
        encoding="utf-8",
    )
    home = tmp_path / "zulip"

    setup_zulip(home=home, env_ref=env, start=False, pull=False, interactive=False)

    assert "SETTING_ZULIP_ADMINISTRATOR: \"admin@example.com\"" in (home / "compose" / "compose.yaml").read_text(
        encoding="utf-8"
    )
