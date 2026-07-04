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
        "codex",
        "cursor-agent",
        "claude",
        "opencode",
        "hermes",
        "lark-cli",
        "docker",
        "zsh",
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
        "chrome",
        "claude",
        "codex",
        "cursor-agent",
        "docker",
        "frp",
        "gitea",
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
    assert "1.0.0" in result.output
    assert "--repo" in result.output
    assert "ChatArch/gitea" in result.output
    assert "--install-dir" in result.output
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
        return target

    monkeypatch.setattr(gitea_setup, "install_gitea_release_binary", fake_install_release_binary)
    monkeypatch.setattr(gitea_setup, "verify_gitea_binary", lambda path, version: f"gitea version {version}")

    result = CliRunner().invoke(
        main,
        ["gitea", "--install-dir", str(tmp_path / "bin"), "--force", "-I"],
    )

    assert result.exit_code == 0, result.output
    assert installed == [
        ("ChatArch/gitea", "1.0.0", tmp_path / "bin", "gitea", True)
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

    target = gitea_setup.install_gitea_release_binary(
        repo="ChatArch/gitea",
        version="1.0.0",
        install_dir=tmp_path,
        binary_name="gitea",
        force=True,
    )

    assert target == tmp_path / "gitea"
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
