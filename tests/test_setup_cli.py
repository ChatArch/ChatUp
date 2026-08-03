import hashlib

import pytest
from click.testing import CliRunner

from chatup.cli import main


def test_chatup_root_help_lists_setup_commands_without_setup_group_or_alias():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    for command in [
        "workspace",
        "nodejs",
        "uv",
        "gitea",
        "mysql",
        "nginx",
        "codex",
        "claude",
        "opencode",
        "hermes",
        "lark-cli",
        "crs",
        "docker",
        "zsh",
        "chrome-for-testing",
        "chromedriver",
    ]:
        assert command in result.output
    assert "setup" not in result.output
    assert "\n  alias " not in result.output


def test_chatup_workspace_help_keeps_interactive_flags():
    result = CliRunner().invoke(main, ["workspace", "--help"])

    assert result.exit_code == 0
    assert "--with-chattool" in result.output
    assert "--with-chatblog" in result.output
    assert "--with-memory" in result.output
    assert "-i, --interactive" in result.output
    assert "-I, --no-interactive" in result.output


def test_top_level_setup_commands_expose_help():
    commands = [
        "cc-connect",
        "chrome-for-testing",
        "chromedriver",
        "claude",
        "codex",
        "crs",
        "docker",
        "frp",
        "gitea",
        "mysql",
        "nginx",
        "hermes",
        "lark-cli",
        "nodejs",
        "opencode",
        "uv",
        "workspace",
        "zsh",
    ]

    for command in commands:
        result = CliRunner().invoke(main, [command, "--help"])
        assert result.exit_code == 0, command
        assert "--help" in result.output
        assert "Usage: chatup setup" not in result.output


def test_setup_group_and_alias_command_are_not_registered():
    setup_result = CliRunner().invoke(main, ["setup", "--help"])
    alias_result = CliRunner().invoke(main, ["alias", "--help"])

    assert setup_result.exit_code != 0
    assert "No such command" in setup_result.output
    assert alias_result.exit_code != 0
    assert "No such command" in alias_result.output


def test_opencode_no_longer_exposes_legacy_chatloop_preset():
    result = CliRunner().invoke(main, ["opencode", "--help"])

    assert result.exit_code == 0
    assert "auto-loop" in result.output
    assert "chatloop" not in result.output.lower()


def test_cc_connect_installs_chatarch_package(monkeypatch):
    import chatup.setup.cc_connect as cc_connect

    commands = []
    monkeypatch.setattr(cc_connect, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        cc_connect,
        "should_install_global_npm_package",
        lambda package_name, display_name, **kwargs: (
            package_name == "@chatarch/cc-connect" and display_name == "cc-connect"
        ),
    )

    class Result:
        returncode = 0
        stderr = ""

    def fake_run_npm_command(args):
        commands.append(args)
        return Result()

    monkeypatch.setattr(cc_connect, "run_npm_command", fake_run_npm_command)

    result = CliRunner().invoke(main, ["cc-connect", "-I"])

    assert result.exit_code == 0, result.output
    assert commands == [["install", "-g", "@chatarch/cc-connect"]]


def test_gitea_help_exposes_release_install_options():
    result = CliRunner().invoke(main, ["gitea", "--help"])

    assert result.exit_code == 0
    assert "--version" in result.output
    assert "latest" in result.output
    assert "--repo" in result.output
    assert "ChatArch/gitea" in result.output
    assert "--install-dir" in result.output
    assert "chattea/bin" in result.output
    assert "--init" in result.output
    assert "--service" in result.output
    assert "--force" in result.output


def test_gitea_setup_downloads_chatarch_release_asset(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    installed = []
    monkeypatch.setattr(
        gitea_setup,
        "select_gitea_asset_name",
        lambda: "gitea-1.0.0-linux-amd64.xz",
    )

    def fake_install_release_binary(*, repo, version, install_dir, binary_name, force):
        installed.append((repo, version, install_dir, binary_name, force))
        target = install_dir / binary_name
        install_dir.mkdir(parents=True, exist_ok=True)
        target.write_text("fake gitea")
        return target, "1.0.0"

    monkeypatch.setattr(gitea_setup, "install_gitea_release_binary", fake_install_release_binary)
    monkeypatch.setattr(gitea_setup, "verify_gitea_binary", lambda path, version: f"gitea version {version}")

    result = CliRunner().invoke(
        main,
        ["gitea", "--install-dir", str(tmp_path / "bin"), "--force", "-I"],
    )

    assert result.exit_code == 0, result.output
    assert installed == [
        ("ChatArch/gitea", "latest", tmp_path / "bin", "gitea", True)
    ]
    assert "gitea version 1.0.0" in result.output




def test_gitea_install_verifies_release_checksum(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    archive_bytes = b"compressed-binary"
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    requested = []

    monkeypatch.setattr(
        gitea_setup,
        "select_gitea_asset_name",
        lambda version="1.0.0": "gitea-1.0.0-linux-amd64.xz",
    )

    def fake_download(url, destination):
        requested.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".sha256"):
            destination.write_text(f"{archive_hash}  gitea-1.0.0-linux-amd64.xz\n")
        else:
            destination.write_bytes(archive_bytes)

    monkeypatch.setattr(gitea_setup, "download_release_asset", fake_download)
    monkeypatch.setattr(
        gitea_setup,
        "decompress_xz",
        lambda source, destination: destination.write_text("decompressed"),
    )

    target, resolved_version = gitea_setup.install_gitea_release_binary(
        repo="ChatArch/gitea",
        version="1.0.0",
        install_dir=tmp_path,
        binary_name="gitea",
        force=True,
    )

    assert target == tmp_path / "gitea"
    assert resolved_version == "1.0.0"
    assert target.read_text() == "decompressed"
    assert requested == [
        "https://github.com/ChatArch/gitea/releases/download/v1.0.0/gitea-1.0.0-linux-amd64.xz",
        "https://github.com/ChatArch/gitea/releases/download/v1.0.0/gitea-1.0.0-linux-amd64.xz.sha256",
    ]


def test_gitea_install_keeps_existing_binary_when_decompress_fails(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    archive_bytes = b"compressed-binary"
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    target = tmp_path / "gitea"
    target.write_text("old binary")

    monkeypatch.setattr(
        gitea_setup,
        "select_gitea_asset_name",
        lambda version="1.0.0": "gitea-1.0.0-linux-amd64.xz",
    )

    def fake_download(url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".sha256"):
            destination.write_text(f"{archive_hash}  gitea-1.0.0-linux-amd64.xz\n")
        else:
            destination.write_bytes(archive_bytes)

    def fail_decompress(source, destination):
        destination.write_text("partial new binary")
        raise RuntimeError("bad archive")

    monkeypatch.setattr(gitea_setup, "download_release_asset", fake_download)
    monkeypatch.setattr(gitea_setup, "decompress_xz", fail_decompress)

    with pytest.raises(RuntimeError):
        gitea_setup.install_gitea_release_binary(
            repo="ChatArch/gitea",
            version="1.0.0",
            install_dir=tmp_path,
            binary_name="gitea",
            force=True,
        )

    assert target.read_text() == "old binary"




def test_gitea_install_creates_temp_dir_inside_install_dir(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    archive_bytes = b"compressed-binary"
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    temp_dirs = []

    class FakeTemporaryDirectory:
        def __init__(self, *, prefix, dir):
            temp_dirs.append((prefix, dir))
            self.path = dir / ".chatup-gitea-test"

        def __enter__(self):
            self.path.mkdir(parents=True, exist_ok=True)
            return str(self.path)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(gitea_setup.tempfile, "TemporaryDirectory", FakeTemporaryDirectory)
    monkeypatch.setattr(
        gitea_setup,
        "select_gitea_asset_name",
        lambda version="1.0.0": "gitea-1.0.0-linux-amd64.xz",
    )

    def fake_download(url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".sha256"):
            destination.write_text(f"{archive_hash}  gitea-1.0.0-linux-amd64.xz\n")
        else:
            destination.write_bytes(archive_bytes)

    monkeypatch.setattr(gitea_setup, "download_release_asset", fake_download)
    monkeypatch.setattr(
        gitea_setup,
        "decompress_xz",
        lambda source, destination: destination.write_text("decompressed"),
    )

    gitea_setup.install_gitea_release_binary(
        repo="ChatArch/gitea",
        version="1.0.0",
        install_dir=tmp_path,
        binary_name="gitea",
        force=True,
    )

    assert temp_dirs == [(".chatup-gitea-", tmp_path)]


def test_gitea_init_writes_chattea_compatible_config(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    def fake_install_release_binary(*, repo, version, install_dir, binary_name, force):
        target = install_dir / binary_name
        install_dir.mkdir(parents=True, exist_ok=True)
        target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        target.chmod(0o755)
        return target, "1.0.0"

    monkeypatch.setattr(gitea_setup, "install_gitea_release_binary", fake_install_release_binary)
    monkeypatch.setattr(gitea_setup, "verify_gitea_binary", lambda path, version: f"gitea version {version}")
    monkeypatch.setattr(gitea_setup, "generate_secret", lambda size=48: f"secret-{size}")

    work_dir = tmp_path / "chattea" / "gitea"
    result = CliRunner().invoke(
        main,
        [
            "gitea",
            "--install-dir",
            str(tmp_path / "chattea" / "bin"),
            "--init",
            "--work-dir",
            str(work_dir),
            "--base-url",
            "http://127.0.0.1:3010",
            "--port",
            "3010",
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    config = work_dir / "custom" / "conf" / "app.ini"
    text = config.read_text(encoding="utf-8")
    assert f"WORK_PATH = {work_dir}" in text
    assert "HTTP_ADDR = 127.0.0.1" in text
    assert "HTTP_PORT = 3010" in text
    assert "DB_TYPE = sqlite3" in text
    assert "SECRET_KEY = secret-48" in text
    assert config.stat().st_mode & 0o777 == 0o600


def test_mysql_help_exposes_chatdata_runtime_defaults():
    result = CliRunner().invoke(main, ["mysql", "--help"])

    assert result.exit_code == 0
    assert "8.4.6" in result.output
    assert "3307" in result.output
    assert "127.0.0.1" in result.output
    assert "--start / --no-start" in result.output
    assert "--smoke / --no-smoke" in result.output


def test_mysql_setup_prepares_chatdata_compatible_layout(monkeypatch, tmp_path):
    import chatup.setup.mysql as mysql_setup

    calls = []
    monkeypatch.setattr(
        mysql_setup,
        "export_layout",
        lambda **kwargs: {"instance": str(tmp_path / "instances" / "mysql" / kwargs["name"])},
    )
    monkeypatch.setattr(
        mysql_setup,
        "install_mysql",
        lambda **kwargs: calls.append(("install", kwargs))
        or {"runtime": str(tmp_path / "runtimes" / "mysql" / kwargs["version"]), "reused": False},
    )
    monkeypatch.setattr(
        mysql_setup,
        "init_instance",
        lambda **kwargs: calls.append(("init", kwargs))
        or {"config": str(tmp_path / "instances" / "mysql" / kwargs["name"] / "my.cnf")},
    )
    monkeypatch.setattr(
        mysql_setup,
        "install_service",
        lambda **kwargs: calls.append(("service", kwargs))
        or {"unit": f"chatdata-mysql-{kwargs['name']}.service"},
    )

    result = CliRunner().invoke(
        main,
        ["mysql", "--home", str(tmp_path), "--name", "dev", "--port", "3310", "--no-start"],
    )

    assert result.exit_code == 0, result.output
    assert [name for name, _ in calls] == ["install", "init", "service"]
    assert calls[1][1]["name"] == "dev"
    assert calls[1][1]["port"] == 3310
    assert "chatdata-mysql-dev.service" in result.output


def test_mysql_smoke_requires_start():
    result = CliRunner().invoke(main, ["mysql", "--no-install", "--no-init", "--no-service", "--smoke"])

    assert result.exit_code != 0
    assert "--smoke requires --start" in result.output


def test_nginx_lists_and_renders_templates(tmp_path):
    list_result = CliRunner().invoke(main, ["nginx", "--list"])

    assert list_result.exit_code == 0
    assert "proxy-pass" in list_result.output
    assert "static-root" in list_result.output

    output = tmp_path / "app.conf"
    render_result = CliRunner().invoke(
        main,
        [
            "nginx",
            "proxy-pass",
            str(output),
            "--set",
            "SERVER_NAME=app.local.example.invalid",
            "--set",
            "PROXY_PASS=http://127.0.0.1:12392",
        ],
    )

    assert render_result.exit_code == 0, render_result.output
    text = output.read_text(encoding="utf-8")
    assert "server_name app.local.example.invalid;" in text
    assert "proxy_pass http://127.0.0.1:12392;" in text


def test_nginx_prepares_user_level_chatarch_runtime(tmp_path):
    home = tmp_path / "nginx"
    result = CliRunner().invoke(
        main,
        [
            "nginx",
            "--home",
            str(home),
            "--no-install",
            "--no-service",
            "--port",
            "18080",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (home / "conf" / "nginx.conf").exists()
    assert (home / "conf" / "sites-available" / "default.conf").exists()
    assert (home / "logs").is_dir()
    assert (home / "run").is_dir()
    assert (home / "temp" / "client_body").is_dir()
    config = (home / "conf" / "nginx.conf").read_text(encoding="utf-8")
    site = (home / "conf" / "sites-available" / "default.conf").read_text(encoding="utf-8")
    assert str(home / "logs" / "error.log") in config
    assert str(home / "conf" / "sites-enabled") in config
    assert "listen 127.0.0.1:18080;" in site


def test_nginx_smoke_requires_start():
    result = CliRunner().invoke(main, ["nginx", "--no-install", "--no-init", "--no-service", "--smoke"])

    assert result.exit_code != 0
    assert "--smoke requires --start" in result.output


def test_uv_help_exposes_defaults():
    result = CliRunner().invoke(main, ["uv", "--help"])

    assert result.exit_code == 0
    assert "--venv" in result.output
    assert "--python" in result.output
    assert "~/.chatarch/venv" in result.output or "/.chatarch/venv" in result.output
    assert "3.12" in result.output
    assert "--force" in result.output


def test_uv_setup_creates_default_chatarch_python_env(monkeypatch, tmp_path):
    import chatup.setup.uv as uv_setup

    created = []
    readiness = iter([False, True])
    monkeypatch.setattr(uv_setup, "DEFAULT_VENV_PATH", tmp_path / "default-venv")
    monkeypatch.setattr(uv_setup, "ensure_uv_installed", lambda: "/usr/local/bin/uv")
    monkeypatch.setattr(uv_setup, "is_chatarch_python_ready", lambda path, version: next(readiness))
    monkeypatch.setattr(
        uv_setup,
        "create_chatarch_python_env",
        lambda uv_bin, path, version, *, force=False: created.append((uv_bin, path, version, force)),
    )

    result = uv_setup.setup_uv()

    assert result["status"] == "created"
    assert result["venv"] == str(tmp_path / "default-venv")
    assert result["python_version"] == "3.12"
    assert created == [("/usr/local/bin/uv", tmp_path / "default-venv", "3.12", False)]


def test_uv_setup_accepts_custom_path_python_and_force(monkeypatch, tmp_path):
    import chatup.setup.uv as uv_setup

    target = tmp_path / "custom-venv"
    created = []
    readiness = iter([False, True])
    monkeypatch.setattr(uv_setup, "ensure_uv_installed", lambda: "/opt/bin/uv")
    monkeypatch.setattr(uv_setup, "is_chatarch_python_ready", lambda path, version: next(readiness))
    monkeypatch.setattr(
        uv_setup,
        "create_chatarch_python_env",
        lambda uv_bin, path, version, *, force=False: created.append((uv_bin, path, version, force)),
    )

    result = CliRunner().invoke(main, ["uv", "--venv", str(target), "--python", "3.11", "--force"])

    assert result.exit_code == 0, result.output
    assert created == [("/opt/bin/uv", target, "3.11", True)]


def test_ensure_uv_installed_uses_official_installer_when_missing(monkeypatch):
    import chatup.setup.uv as uv_setup

    monkeypatch.setattr(uv_setup, "find_uv", lambda: None)
    monkeypatch.setattr(uv_setup, "install_uv_with_official_script", lambda: "/home/me/.local/bin/uv")

    assert uv_setup.ensure_uv_installed() == "/home/me/.local/bin/uv"


def test_create_chatarch_python_env_seeds_pip_and_force_clears(monkeypatch, tmp_path):
    import chatup.setup.uv as uv_setup

    commands = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run_command(command, **kwargs):
        commands.append(command)
        return Result()

    monkeypatch.setattr(uv_setup, "_run_command", fake_run_command)

    uv_setup.create_chatarch_python_env("uv", tmp_path / "venv", "3.12", force=True)

    assert commands == [
        ["uv", "python", "install", "3.12"],
        ["uv", "venv", "--python", "3.12", "--seed", "--clear", "--force", str(tmp_path / "venv")],
    ]


def test_create_chatarch_python_env_allows_existing_same_version_venv(monkeypatch, tmp_path):
    import chatup.setup.uv as uv_setup

    target = tmp_path / "venv"
    target.mkdir()
    commands = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run_command(command, **kwargs):
        commands.append(command)
        return Result()

    monkeypatch.setattr(uv_setup, "_run_command", fake_run_command)

    uv_setup.create_chatarch_python_env("uv", target, "3.12", force=False)

    assert commands == [
        ["uv", "python", "install", "3.12"],
        ["uv", "venv", "--python", "3.12", "--seed", "--allow-existing", str(target)],
    ]
