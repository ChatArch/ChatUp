from __future__ import annotations

import json
import os
import subprocess

import pytest
from click.testing import CliRunner
from chatenv.paths import get_paths
from chatenv.store import EnvStore

from chatup.cli import main
from chatup.config import CursorAgentConfig
from chatup.setup.cursor_agent import setup_cursor_agent


def _set_test_home(monkeypatch, home):
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _is_windows() -> bool:
    return os.name == "nt"


def _assert_private_file(path):
    if not _is_windows():
        assert path.stat().st_mode & 0o777 == 0o600


def _install_fake_cursor_agent(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    binary = bin_dir / ("cursor-agent.cmd" if _is_windows() else "cursor-agent")
    if _is_windows():
        binary.write_text("@echo off\necho test-cursor-agent\n", encoding="utf-8")
    else:
        binary.write_text(
            "#!/usr/bin/env bash\n"
            "case \"${1:-}\" in --version) echo test-cursor-agent ;; *) echo test-cursor-agent ;; esac\n",
            encoding="utf-8",
        )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")]))
    return binary


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
        "-e, --env",
        "--cli-config",
        "--api-key-env",
        "--credential-store",
        "--env-profile",
        "--save-profile",
        "--install-only",
        "-i, --interactive / -I, --no-interactive",
    ]:
        assert expected in result.output


def test_cursor_agent_resolves_standard_user_bin_when_path_omits_it(tmp_path, monkeypatch):
    home = tmp_path / "home"
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    binary = bin_dir / ("cursor-agent.cmd" if _is_windows() else "cursor-agent")
    if _is_windows():
        binary.write_text("@echo off\necho test-cursor-agent\n", encoding="utf-8")
    else:
        binary.write_text("#!/usr/bin/env bash\necho test-cursor-agent\n", encoding="utf-8")
    binary.chmod(0o755)
    _set_test_home(monkeypatch, home)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    result = setup_cursor_agent(install_only=True, verify=False, interactive=False)

    assert result["installed_binary"] is False
    assert result["binary"] == str(binary)


def test_cursor_agent_auth_env_writes_auth_json_with_restrictive_mode(tmp_path, monkeypatch):
    home = tmp_path / "home"
    env_path = tmp_path / "cursor.env"
    env_path.write_text(
        "CURSOR_ACCESS_TOKEN=access-secret\nCURSOR_REFRESH_TOKEN=refresh-secret\n",
        encoding="utf-8",
    )
    _set_test_home(monkeypatch, home)
    _install_fake_cursor_agent(tmp_path, monkeypatch)

    result = setup_cursor_agent(
        auth_env=env_path,
        install_only=False,
        verify=False,
        interactive=False,
    )

    auth_path = home / ".config" / "cursor" / "auth.json"
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert data == {"accessToken": "access-secret", "refreshToken": "refresh-secret"}
    _assert_private_file(auth_path)
    assert result["auth_json_written"] is True
    assert "access-secret" not in json.dumps(result)
    assert "refresh-secret" not in json.dumps(result)


def test_cursor_agent_env_ref_file_writes_auth_json(tmp_path, monkeypatch):
    home = tmp_path / "home"
    env_path = tmp_path / "cursor.env"
    env_path.write_text(
        "CURSOR_ACCESS_TOKEN=env-access\nCURSOR_REFRESH_TOKEN=env-refresh\n",
        encoding="utf-8",
    )
    _set_test_home(monkeypatch, home)
    _install_fake_cursor_agent(tmp_path, monkeypatch)

    result = setup_cursor_agent(
        env_ref=env_path,
        install_only=False,
        verify=False,
        interactive=False,
    )

    auth_path = home / ".config" / "cursor" / "auth.json"
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert data == {"accessToken": "env-access", "refreshToken": "env-refresh"}
    _assert_private_file(auth_path)
    assert result["auth_json_written"] is True
    assert result["env_profile_loaded"] is False
    assert "env-access" not in json.dumps(result)
    assert "env-refresh" not in json.dumps(result)


def test_cursor_agent_env_ref_profile_loads_auth(tmp_path, monkeypatch):
    home = tmp_path / "home"
    chatarch_home = tmp_path / "chatarch"
    _set_test_home(monkeypatch, home)
    monkeypatch.setenv("CHATARCH_HOME", str(chatarch_home))
    _install_fake_cursor_agent(tmp_path, monkeypatch)
    store = EnvStore(get_paths().envs_dir)
    store.save_profile(
        CursorAgentConfig,
        "cursor-fast",
        {
            "CURSOR_ACCESS_TOKEN": "fast-access",
            "CURSOR_REFRESH_TOKEN": "fast-refresh",
            "CURSOR_CREDENTIAL_STORE": "native",
        },
    )

    result = setup_cursor_agent(env_ref="cursor-fast", verify=False, interactive=False)

    auth_path = home / ".config" / "cursor" / "auth.json"
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert data == {"accessToken": "fast-access", "refreshToken": "fast-refresh"}
    _assert_private_file(auth_path)
    assert result["env_profile_loaded"] is True
    assert result["auth_json_written"] is True
    assert "fast-access" not in json.dumps(result)
    assert "fast-refresh" not in json.dumps(result)


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
    _set_test_home(monkeypatch, home)
    _install_fake_cursor_agent(tmp_path, monkeypatch)

    result = setup_cursor_agent(
        auth_json=source_auth,
        cli_config=source_config,
        install_only=False,
        verify=False,
        interactive=False,
    )

    auth_path = home / ".config" / "cursor" / "auth.json"
    config_path = home / ".cursor" / "cli-config.json"
    _assert_private_file(auth_path)
    _assert_private_file(config_path)
    assert result["auth_json_written"] is True
    assert result["cli_config_written"] is True


def test_cursor_agent_file_wrapper_reads_auth_json_without_storing_secret(tmp_path, monkeypatch):
    if _is_windows():
        pytest.skip("POSIX wrapper execution uses bash; Windows .cmd wrapper is covered separately.")
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
    _set_test_home(monkeypatch, home)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

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


def test_cursor_agent_loads_auth_from_chatenv_profile(tmp_path, monkeypatch):
    home = tmp_path / "home"
    chatarch_home = tmp_path / "chatarch"
    _set_test_home(monkeypatch, home)
    monkeypatch.setenv("CHATARCH_HOME", str(chatarch_home))
    _install_fake_cursor_agent(tmp_path, monkeypatch)
    store = EnvStore(get_paths().envs_dir)
    store.save_profile(
        CursorAgentConfig,
        "cursor-work",
        {
            "CURSOR_ACCESS_TOKEN": "profile-access",
            "CURSOR_REFRESH_TOKEN": "profile-refresh",
            "CURSOR_CREDENTIAL_STORE": "native",
        },
    )

    result = setup_cursor_agent(env_profile="cursor-work", verify=False, interactive=False)

    auth_path = home / ".config" / "cursor" / "auth.json"
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert data == {"accessToken": "profile-access", "refreshToken": "profile-refresh"}
    _assert_private_file(auth_path)
    assert result["env_profile_loaded"] is True
    assert result["auth_json_written"] is True
    assert "profile-access" not in json.dumps(result)
    assert "profile-refresh" not in json.dumps(result)


def test_cursor_agent_saves_imported_auth_to_chatenv_profile(tmp_path, monkeypatch):
    home = tmp_path / "home"
    chatarch_home = tmp_path / "chatarch"
    env_path = tmp_path / "cursor.env"
    env_path.write_text(
        "CURSOR_ACCESS_TOKEN=save-access\nCURSOR_REFRESH_TOKEN=save-refresh\n",
        encoding="utf-8",
    )
    _set_test_home(monkeypatch, home)
    monkeypatch.setenv("CHATARCH_HOME", str(chatarch_home))
    _install_fake_cursor_agent(tmp_path, monkeypatch)

    result = setup_cursor_agent(
        auth_env=env_path,
        save_profile="cursor-saved",
        credential_store="native",
        verify=False,
        interactive=False,
    )

    values = EnvStore(get_paths().envs_dir).load_profile(CursorAgentConfig, "cursor-saved")
    assert values["CURSOR_ACCESS_TOKEN"] == "save-access"
    assert values["CURSOR_REFRESH_TOKEN"] == "save-refresh"
    assert values["CURSOR_CREDENTIAL_STORE"] == "native"
    assert result["profile_saved"]
    # ChatEnv owns profile file storage and permission semantics; ChatUp only verifies values round-trip.
    assert "save-access" not in json.dumps(result)
    assert "save-refresh" not in json.dumps(result)
