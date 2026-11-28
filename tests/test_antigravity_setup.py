"""Offline coverage for the official Antigravity bootstrapper workflow."""
from pathlib import Path
import subprocess
import urllib.error

import pytest

from chatup.setup import antigravity


@pytest.fixture
def install(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(antigravity.Path, "home", lambda: home)
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch"))
    monkeypatch.setattr(antigravity.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(antigravity.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(antigravity.shutil, "which", lambda name: f"/mock/{name}")
    return home


@pytest.mark.parametrize("system,machine", [
    ("Darwin", "arm64"), ("Darwin", "x86_64"),
    ("Linux", "aarch64"), ("Linux", "amd64"),
])
def test_unix_plan_uses_official_location_and_bootstrapper(install, monkeypatch, system, machine):
    monkeypatch.setattr(antigravity.platform, "system", lambda: system)
    monkeypatch.setattr(antigravity.platform, "machine", lambda: machine)
    plan = antigravity.plan_antigravity_cli_install()
    assert plan["binary"] == str(install / ".local" / "bin" / "agy")
    assert plan["url"] == "https://antigravity.google/cli/install.sh"


def test_custom_directory_is_expanded_and_resolved(install):
    plan = antigravity.plan_antigravity_cli_install(install_dir="~/custom bin")
    assert plan["binary"] == str(Path("~").expanduser() / "custom bin" / "agy")


def test_windows_plan_uses_official_powershell_and_localappdata(install, monkeypatch, tmp_path):
    monkeypatch.setattr(antigravity.platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local AppData"))
    plan = antigravity.plan_antigravity_cli_install()
    assert plan["binary"] == str(tmp_path / "Local AppData" / "agy" / "bin" / "agy.exe")
    assert plan["url"] == "https://antigravity.google/cli/install.ps1"


@pytest.mark.parametrize("system,machine,expected", [
    ("FreeBSD", "amd64", "does not support"), ("Linux", "i386", "architecture"),
])
def test_unsupported_platform_is_rejected_before_io(install, monkeypatch, system, machine, expected):
    monkeypatch.setattr(antigravity.platform, "system", lambda: system)
    monkeypatch.setattr(antigravity.platform, "machine", lambda: machine)
    monkeypatch.setattr(antigravity, "_cache_dir", lambda: pytest.fail("must not write"))
    monkeypatch.setattr(antigravity, "_run", lambda *a, **k: pytest.fail("must not run"))
    with pytest.raises(RuntimeError, match=expected):
        antigravity.setup_antigravity_cli()


def test_dry_run_never_downloads_executes_or_creates_cache(install, monkeypatch, tmp_path):
    monkeypatch.setattr(antigravity, "_cache_dir", lambda: pytest.fail("must not create cache"))
    monkeypatch.setattr(antigravity, "_download_installer", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(antigravity, "_run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(antigravity.shutil, "which", lambda *a: pytest.fail("must not resolve shell"))
    result = antigravity.setup_antigravity_cli(dry_run=True)
    assert result["status"] == "planned" and result["verified"] is False
    assert list(install.iterdir()) == []
    assert not (tmp_path / "chatarch").exists()


def make_binary(binary):
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"binary fixture")
    binary.chmod(0o755)


@pytest.mark.parametrize("system,custom", [("Darwin", False), ("Linux", True), ("Windows", False), ("Windows", True)])
def test_fresh_install_uses_cached_script_and_verifies_exact_target(install, monkeypatch, tmp_path, system, custom):
    monkeypatch.setattr(antigravity.platform, "system", lambda: system)
    monkeypatch.setenv("LOCALAPPDATA", str(install / "AppData" / "Local"))
    directory = tmp_path / "custom bin" if custom else None
    plan = antigravity.plan_antigravity_cli_install(install_dir=directory)
    binary = Path(plan["binary"])
    calls = []

    def download(url, destination):
        assert url == plan["url"]
        assert tmp_path / "chatarch" / "cache" / "antigravity" in destination.parents
        destination.write_bytes(b"official bootstrapper fixture")
        calls.append(("download", str(destination)))

    def run(command, **kwargs):
        calls.append(("run", command))
        if command[-1] == "--version":
            assert command == [str(binary), "--version"]
            assert kwargs["timeout"] == 30
            return subprocess.CompletedProcess(command, 0, "1.5.18\n", "")
        assert command[-2:] == ["--dir", str(binary.parent)]
        assert kwargs["timeout"] == 600
        script = Path(command[-3])
        assert script.is_file()
        if system == "Windows":
            assert command[:6] == ["/mock/powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]
        else:
            assert command[0] == "/mock/bash"
        make_binary(binary)
        return subprocess.CompletedProcess(command, 0, "installed", "")

    monkeypatch.setattr(antigravity, "_download_installer", download)
    monkeypatch.setattr(antigravity, "_run", run)
    result = antigravity.setup_antigravity_cli(install_dir=directory)
    assert result["status"] == "installed" and result["verified"] is True
    assert result["version"] == "1.5.18"
    assert len(calls) == 3
    assert not Path(calls[0][1]).exists()
    assert list((tmp_path / "chatarch" / "cache" / "antigravity").iterdir()) == []


def test_existing_default_outside_path_is_verified_without_installation(install, monkeypatch):
    binary = install / ".local" / "bin" / "agy"
    make_binary(binary)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(antigravity.shutil, "which", lambda *a: pytest.fail("existing target needs no PATH lookup"))
    monkeypatch.setattr(antigravity, "_cache_dir", lambda: pytest.fail("must not create cache"))
    monkeypatch.setattr(antigravity, "_download_installer", lambda *a: pytest.fail("must not download"))

    def run(command, **kwargs):
        assert command == [str(binary), "--version"]
        return subprocess.CompletedProcess(command, 0, "1.5.18\n", "")

    monkeypatch.setattr(antigravity, "_run", run)
    result = antigravity.setup_antigravity_cli()
    assert result["status"] == "already_installed" and result["version"] == "1.5.18"
    assert binary.read_bytes() == b"binary fixture"


@pytest.mark.parametrize("output", ["not a version", "other tool 1.2.3", ""])
def test_invalid_existing_binary_is_preserved(install, monkeypatch, output):
    binary = install / ".local" / "bin" / "agy"
    make_binary(binary)
    monkeypatch.setattr(antigravity, "_download_installer", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(antigravity, "_run", lambda command, **k: subprocess.CompletedProcess(command, 0, output, ""))
    with pytest.raises(RuntimeError, match="invalid and was not overwritten"):
        antigravity.setup_antigravity_cli()
    assert binary.read_bytes() == b"binary fixture"


def test_installer_success_without_binary_is_not_reported_as_installed(install, monkeypatch):
    monkeypatch.setattr(antigravity, "_download_installer", lambda url, path: path.write_bytes(b"script"))
    monkeypatch.setattr(antigravity, "_run", lambda command, **k: subprocess.CompletedProcess(command, 0, "done", ""))
    with pytest.raises(RuntimeError, match="executable is missing"):
        antigravity.setup_antigravity_cli()


@pytest.mark.parametrize("failure", [
    urllib.error.URLError("offline"), OSError("permission denied"),
    subprocess.TimeoutExpired("bash", 600), RuntimeError("installer exit 7"),
])
def test_download_and_install_failures_are_runtime_errors_and_cleanup_cache(install, monkeypatch, tmp_path, failure):
    def download(url, destination):
        destination.write_bytes(b"partial script")
        if isinstance(failure, urllib.error.URLError):
            raise failure

    def run(command, **kwargs):
        raise failure

    monkeypatch.setattr(antigravity, "_download_installer", download)
    monkeypatch.setattr(antigravity, "_run", run)
    with pytest.raises(RuntimeError):
        antigravity.setup_antigravity_cli()
    assert list((tmp_path / "chatarch" / "cache" / "antigravity").iterdir()) == []


def test_missing_shell_fails_before_download(install, monkeypatch):
    monkeypatch.setattr(antigravity.shutil, "which", lambda *a: None)
    monkeypatch.setattr(antigravity, "_download_installer", lambda *a: pytest.fail("must not download"))
    with pytest.raises(RuntimeError, match="Bash is required"):
        antigravity.setup_antigravity_cli()


def test_run_reports_nonzero_exit_without_success(install, monkeypatch):
    monkeypatch.setattr(antigravity.subprocess, "run", lambda command, **k: subprocess.CompletedProcess(command, 7, "", "checksum mismatch"))
    with pytest.raises(RuntimeError, match="exit 7.*checksum mismatch"):
        antigravity._run(["bash", "install.sh"], timeout=600)
