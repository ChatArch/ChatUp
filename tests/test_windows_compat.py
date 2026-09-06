from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from click.testing import CliRunner

from chatup.cli import main
from chatup.utils import platforming


def test_uv_windows_installer_uses_powershell(monkeypatch):
    import chatup.setup.uv as uv_setup

    commands = []

    def fake_run_command(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(uv_setup, "_run_command", fake_run_command)
    monkeypatch.setattr(uv_setup, "find_uv", lambda: r"C:\Users\me\.local\bin\uv.exe")

    assert uv_setup.install_uv_with_official_script().endswith("uv.exe")
    assert commands == [
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://astral.sh/uv/install.ps1 | iex",
        ]
    ]
    assert platforming.venv_python_path(Path("C:/chatarch/venv")).parts[-2:] == (
        "Scripts",
        "python.exe",
    )
    assert platforming.venv_activate_hint(Path("C:/chatarch/venv")).endswith(
        str(Path("Scripts") / "Activate.ps1")
    )


def test_nodejs_windows_reuses_path_runtime(monkeypatch):
    import chatup.setup.nodejs as nodejs_setup

    runtime = nodejs_setup._build_runtime(
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files\nodejs\npm.cmd",
        "v22.11.0",
        "10.9.0",
        "path",
    )
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "_detect_nodejs_runtime", lambda: runtime)

    result = CliRunner().invoke(main, ["nodejs"])

    assert result.exit_code == 0, result.output
    assert "ChatUp reuses node/npm from PATH on Windows" in result.output


def test_docker_windows_prints_desktop_guidance(monkeypatch):
    import chatup.setup.docker as docker_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(docker_setup, "_docker_version", lambda: None)
    monkeypatch.setattr(docker_setup, "_docker_compose_version", lambda: None)

    result = CliRunner().invoke(main, ["docker", "-I"])

    assert result.exit_code == 0, result.output
    assert "Install Docker Desktop for Windows" in result.output
    assert "Docker group/systemd checks are skipped on Windows" in result.output


def test_mysql_windows_uses_zip_and_tcp_config(monkeypatch, tmp_path):
    import chatup.setup.mysql as mysql_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(mysql_setup.platform, "system", lambda: "Windows")
    monkeypatch.setattr(mysql_setup.platform, "machine", lambda: "AMD64")

    assert mysql_setup.detect_mysql_platform() == "winx64"
    url, checksum = mysql_setup.mysql_asset_urls("8.4.6")
    assert url.endswith("mysql-8.4.6-winx64.zip")
    assert checksum.endswith("mysql-8.4.6-winx64.zip.md5")

    layout = mysql_setup.mysql_layout(home=tmp_path)
    config = mysql_setup.render_my_cnf(layout, tmp_path / "runtime")
    assert "socket=" not in config
    assert "host=127.0.0.1" in config
    assert mysql_setup.client_command(home=tmp_path)[:2] == [
        str(tmp_path / "runtimes" / "mysql" / "8.4.6" / "bin" / "mysql.exe"),
        "-uroot",
    ]


def test_gitea_windows_service_fails_before_systemctl(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    target = tmp_path / "gitea.exe"
    target.write_text("binary", encoding="utf-8")
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(
        gitea_setup,
        "install_gitea_release_binary",
        lambda **kwargs: (target, "1.0.0"),
    )
    monkeypatch.setattr(
        gitea_setup,
        "verify_gitea_binary",
        lambda path, version: f"gitea version {version}",
    )

    result = CliRunner().invoke(main, ["gitea", "--service", "-I"])

    assert result.exit_code != 0
    assert "systemd services" in result.output


def test_frp_windows_zip_extracts_exe(monkeypatch, tmp_path):
    import chatup.setup.frp as frp_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    archive = tmp_path / "frp.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("frp_0.66.0_windows_amd64/frpc.exe", b"binary")

    extracted = Path(frp_setup.extract_frp(archive, tmp_path / "out", "frpc.exe"))

    assert extracted == tmp_path / "out" / "frpc.exe"
    assert extracted.read_bytes() == b"binary"
