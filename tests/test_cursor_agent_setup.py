from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from chatup.cli import main


def test_root_help_lists_cursor_agent_command():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "cursor-agent" in result.output
    assert "Cursor Agent CLI" in result.output


def test_cursor_agent_help_exposes_auth_copy_options():
    result = CliRunner().invoke(main, ["cursor-agent", "--help"])

    assert result.exit_code == 0
    assert "--auth-json" in result.output
    assert "--auth-env" in result.output
    assert "--cli-config" in result.output
    assert "--api-key-env" in result.output
    assert "--install-only" in result.output
    assert "-i, --interactive" in result.output
    assert "-I, --no-interactive" in result.output


def test_cursor_agent_setup_writes_auth_from_env_file_without_printing_secret(monkeypatch, tmp_path):
    import chatup.setup.cursor_agent as cursor_agent

    fake_home = tmp_path / "home"
    env_file = tmp_path / "cursor.env"
    env_file.write_text(
        "export CURSOR_ACCESS_TOKEN='access-secret-value'\n"
        "export CURSOR_REFRESH_TOKEN=refresh-secret-value\n",
        encoding="utf-8",
    )
    copied_configs = []
    verified = []

    monkeypatch.setattr(cursor_agent.Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr(cursor_agent, "find_cursor_agent", lambda: "/fake/bin/agent")
    monkeypatch.setattr(cursor_agent, "install_cursor_agent_with_official_script", lambda: "/fake/bin/agent")
    monkeypatch.setattr(cursor_agent, "verify_cursor_agent", lambda agent_bin: verified.append(agent_bin))
    monkeypatch.setattr(cursor_agent, "copy_cli_config", lambda source, target: copied_configs.append((source, target)) or ["cli-config"])

    result = CliRunner().invoke(main, ["cursor-agent", "--auth-env", str(env_file), "-I"])

    assert result.exit_code == 0, result.output
    auth_path = fake_home / ".config/cursor/auth.json"
    assert auth_path.exists()
    assert auth_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(auth_path.read_text()) == {
        "accessToken": "access-secret-value",
        "refreshToken": "refresh-secret-value",
    }
    assert verified == ["/fake/bin/agent"]
    assert "access-secret-value" not in result.output
    assert "refresh-secret-value" not in result.output
    assert "Updated Cursor Agent secret keys: accessToken, refreshToken" in result.output


def test_cursor_agent_setup_copies_auth_json_and_cli_config(monkeypatch, tmp_path):
    import chatup.setup.cursor_agent as cursor_agent

    fake_home = tmp_path / "home"
    source_auth = tmp_path / "auth.json"
    source_cli = tmp_path / "cli-config.json"
    source_auth.write_text(
        json.dumps({"accessToken": "source-access", "refreshToken": "source-refresh"}),
        encoding="utf-8",
    )
    source_cli.write_text(json.dumps({"version": 1, "selectedModel": {"modelId": "gpt-5.5-high"}}), encoding="utf-8")
    verified = []

    monkeypatch.setattr(cursor_agent.Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr(cursor_agent, "find_cursor_agent", lambda: "/fake/bin/agent")
    monkeypatch.setattr(cursor_agent, "install_cursor_agent_with_official_script", lambda: "/fake/bin/agent")
    monkeypatch.setattr(cursor_agent, "verify_cursor_agent", lambda agent_bin: verified.append(agent_bin))

    result = CliRunner().invoke(
        main,
        [
            "cursor-agent",
            "--auth-json",
            str(source_auth),
            "--cli-config",
            str(source_cli),
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads((fake_home / ".config/cursor/auth.json").read_text()) == {
        "accessToken": "source-access",
        "refreshToken": "source-refresh",
    }
    assert json.loads((fake_home / ".cursor/cli-config.json").read_text()) == {
        "version": 1,
        "selectedModel": {"modelId": "gpt-5.5-high"},
    }
    assert (fake_home / ".config/cursor/auth.json").stat().st_mode & 0o777 == 0o600
    assert (fake_home / ".cursor/cli-config.json").stat().st_mode & 0o777 == 0o600
    assert verified == ["/fake/bin/agent"]
    assert "source-access" not in result.output
    assert "source-refresh" not in result.output
    assert "Auth: " in result.output
    assert "Config: " in result.output


def test_cursor_agent_setup_installs_when_agent_missing(monkeypatch, tmp_path):
    import chatup.setup.cursor_agent as cursor_agent

    fake_home = tmp_path / "home"
    installed = []
    verified = []

    monkeypatch.setattr(cursor_agent.Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr(cursor_agent, "find_cursor_agent", lambda: None)
    monkeypatch.setattr(cursor_agent, "install_cursor_agent_with_official_script", lambda: installed.append(True) or "/installed/agent")
    monkeypatch.setattr(cursor_agent, "verify_cursor_agent", lambda agent_bin: verified.append(agent_bin))

    result = CliRunner().invoke(main, ["cursor-agent", "--install-only", "-I"])

    assert result.exit_code == 0, result.output
    assert installed == [True]
    assert verified == ["/installed/agent"]
    assert "Cursor Agent install completed." in result.output
