from __future__ import annotations

import json
from pathlib import Path
import os
import subprocess

from click.testing import CliRunner

from chatup.cli import main
from chatup.setup.cursor_agent import setup_cursor_agent


def test_root_help_lists_cursor_agent_command():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "cursor-agent" in result.output
    assert "Cursor Agent CLI" in result.output


def test_cursor_agent_help_exposes_safe_auth_options():
    result = CliRunner().invoke(main, ["cursor-agent", "--help"])

    assert result.exit_code == 0
    for expected in [
        "--auth-json",
        "--auth-env",
        "--cli-config",
        "--api-key-env",
        "--credential-store",
        "--install-only",
        "-i, --interactive / -I, --no-interactive",
    ]:
        assert expected in result.output


def test_cursor_agent_auth_env_writes_auth_json_with_restrictive_mode(tmp_path, monkeypatch):
    home = tmp_path / "home"
    env_path = tmp_path / "cursor.env"
    env_path.write_text(
        "CURSOR_ACCESS_TOKEN=access-secret\nCURSOR_REFRESH_TOKEN=refresh-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))

    result = setup_cursor_agent(
        auth_env=env_path,
        install_only=False,
        verify=False,
        interactive=False,
    )

    auth_path = home / ".config" / "cursor" / "auth.json"
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert data == {"accessToken": "access-secret", "refreshToken": "refresh-secret"}
    assert auth_path.stat().st_mode & 0o777 == 0o600
    assert result["auth_json_written"] is True
    assert "access-secret" not in json.dumps(result)
    assert "refresh-secret" not in json.dumps(result)


def test_cursor_agent_copies_auth_json_and_cli_config_with_restrictive_mode(tmp_path, monkeypatch):
    home = tmp_path / "home"
    source_auth = tmp_path / "auth.json"
    source_config = tmp_path / "cli-config.json"
    source_auth.write_text(
        json.dumps({"accessToken": "a", "refreshToken": "r"}),
        encoding="utf-8",
    )
    source_config.write_text(
        json.dumps({"authInfo": {"email": "user@example.com"}, "selectedModel": {"modelId": "gpt-5"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))

    result = setup_cursor_agent(
        auth_json=source_auth,
        cli_config=source_config,
        install_only=False,
        verify=False,
        interactive=False,
    )

    auth_path = home / ".config" / "cursor" / "auth.json"
    config_path = home / ".cursor" / "cli-config.json"
    assert auth_path.stat().st_mode & 0o777 == 0o600
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert result["auth_json_written"] is True
    assert result["cli_config_written"] is True


def test_cursor_agent_file_wrapper_reads_auth_json_without_storing_secret(tmp_path, monkeypatch):
    home = tmp_path / "home"
    bin_dir = home / ".local" / "bin"
    version_dir = home / ".local" / "share" / "cursor-agent" / "versions" / "test-version"
    bin_dir.mkdir(parents=True)
    version_dir.mkdir(parents=True)
    official = version_dir / "cursor-agent"
    official.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s:%s:%s\\n' \"${AGENT_CLI_CREDENTIAL_STORE:-}\" \"${CURSOR_AUTH_TOKEN:-}\" \"$1\"\n",
        encoding="utf-8",
    )
    official.chmod(0o755)
    entrypoint = bin_dir / "cursor-agent"
    entrypoint.symlink_to(official)
    source_auth = tmp_path / "auth.json"
    source_auth.write_text(
        json.dumps({"accessToken": "access-secret", "refreshToken": "refresh-secret"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(bin_dir))

    result = setup_cursor_agent(
        auth_json=source_auth,
        credential_store="file-wrapper",
        install_only=False,
        verify=False,
        interactive=False,
    )

    wrapper_text = entrypoint.read_text(encoding="utf-8")
    assert result["wrapper_written"] is True
    assert entrypoint.stat().st_mode & 0o777 == 0o755
    assert "access-secret" not in wrapper_text
    assert "refresh-secret" not in wrapper_text
    proc = subprocess.run(
        [str(entrypoint), "models"],
        text=True,
        capture_output=True,
        check=False,
        env={"HOME": str(home), "PATH": os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "file:access-secret:models"
