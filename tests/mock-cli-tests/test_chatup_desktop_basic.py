import importlib
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import zipfile

import pytest
from click.testing import CliRunner

from chatup.cli import main


@pytest.fixture
def desktop(monkeypatch):
    module = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(module.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(module.platform, "mac_ver", lambda: ("15.0", (), ""))
    return module


@pytest.mark.parametrize("app", ["chrome", "iterm"])
def test_mac_dry_run_does_not_need_brew_or_touch_disk(desktop, monkeypatch, app):
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not run a process"))
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("must not create cache"))
    monkeypatch.setattr(desktop.shutil, "which", lambda _: pytest.fail("must not need Homebrew"))
    result = CliRunner().invoke(main, [app, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert desktop.MAC_APPS[app]["url"] in result.output
    assert "Dry run" in result.output
    assert "Installation verified" not in result.output


@pytest.mark.parametrize("system", ["Linux", "Windows", "FreeBSD"])
def test_iterm_rejects_other_platforms_before_any_side_effect(desktop, monkeypatch, system):
    monkeypatch.setattr(desktop.platform, "system", lambda: system)
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    result = CliRunner().invoke(main, ["iterm"])
    assert result.exit_code != 0
    assert "macOS only" in result.output


@pytest.mark.parametrize("manager,extension", [("apt-get", "deb"), ("dnf", "rpm"), ("yum", "rpm"), ("zypper", "rpm")])
def test_linux_plan_selects_native_manager_and_explicit_sudo(desktop, monkeypatch, manager, extension):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Linux")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(desktop, "_is_root", lambda: False)
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/usr/bin/{name}" if name == manager else None)
    plan = desktop.plan_desktop_install("chrome", sudo=True, yes=True)
    assert plan["url"].startswith("https://dl.google.com/linux/direct/")
    assert plan["url"].endswith("." + extension)
    assert plan["command"][:2] == ["sudo", manager]
    assert ("--non-interactive" if manager == "zypper" else "-y") in plan["command"]
    assert "sudo" not in desktop.plan_desktop_install("chrome")["command"]


@pytest.mark.parametrize("system,machine,expected", [("Linux", "aarch64", "x86_64"), ("FreeBSD", "amd64", "not supported"), ("Darwin", "ppc", "architecture")])
def test_chrome_rejects_unsupported_platforms(desktop, monkeypatch, system, machine, expected):
    monkeypatch.setattr(desktop.platform, "system", lambda: system)
    monkeypatch.setattr(desktop.platform, "machine", lambda: machine)
    result = CliRunner().invoke(main, ["chrome", "--dry-run"])
    assert result.exit_code != 0
    assert expected in result.output


def make_bundle(path, spec):
    contents = path / "Contents"
    binary = contents / "MacOS" / spec["app"]
    binary.parent.mkdir(parents=True)
    binary.write_text("executable fixture", encoding="utf-8")
    binary.chmod(0o755)
    (contents / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": spec["bundle_id"], "CFBundleExecutable": spec["app"],
        "CFBundleShortVersionString": "123.4.5", "LSMinimumSystemVersion": "14.0",
    }))


@pytest.fixture
def mac_install(desktop, monkeypatch, tmp_path):
    # Keep simulated app bundles out of macOS application search results.
    tmp_path = tmp_path / "desktop.noindex"
    tmp_path.mkdir()
    apps = tmp_path / "Applications"
    apps.mkdir()
    user_apps = tmp_path / "user" / "Applications"
    monkeypatch.setattr(desktop, "_mac_app_dirs", lambda: (apps, user_apps))
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(desktop, "_cache_dir", lambda: cache)
    calls = []

    def download(url, archive):
        spec = next(s for s in desktop.MAC_APPS.values() if s["url"] == url)
        fixture = tmp_path / "source" / spec["bundle"]
        make_bundle(fixture, spec)
        calls.append(["download", url])
        if spec["format"] == "zip":
            with zipfile.ZipFile(archive, "w") as bundle:
                for path in fixture.rglob("*"):
                    bundle.write(path, path.relative_to(fixture.parent))
        else:
            archive.write_bytes(b"disk image fixture")

    def run(command, **kwargs):
        calls.append(command)
        if command[0].endswith("hdiutil") and command[1] == "attach":
            mount = Path(command[command.index("-mountpoint") + 1])
            for source in (tmp_path / "source").iterdir():
                shutil.copytree(source, mount / source.name)
        elif command[0].endswith("ditto"):
            shutil.copytree(command[1], command[2], symlinks=True)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(desktop, "_download", download)
    monkeypatch.setattr(desktop, "_run", run)
    yield apps, user_apps, cache, calls
    shutil.rmtree(tmp_path)


@pytest.mark.parametrize("app", ["chrome", "iterm", "snipaste"])
def test_mac_install_verifies_and_is_idempotent(desktop, mac_install, app):
    apps, _, cache, calls = mac_install
    first = desktop.setup_desktop_app(app)
    assert first["status"] == "installed"
    assert first["verified"] is True
    assert first["version"] == "123.4.5"
    assert Path(first["path"]) == apps / desktop.MAC_APPS[app]["bundle"]
    assert not list(cache.iterdir())
    assert any(command[0].endswith("codesign") and desktop.MAC_APPS[app]["team_id"] in command[-2] for command in calls)
    assert all(command[-2].startswith("=anchor ") for command in calls if command[0].endswith("codesign"))
    if desktop.MAC_APPS[app]["format"] == "dmg":
        assert calls[-1][1] == "detach"
    calls.clear()
    args = ["macos", "--app", "snipaste", "-I"] if app == "snipaste" else [app]
    repeated = CliRunner().invoke(main, args)
    assert repeated.exit_code == 0, repeated.output
    assert "Already installed" in repeated.output
    assert all(command[0].endswith("codesign") for command in calls)


def test_mac_reuses_user_application(desktop, mac_install):
    _, user_apps, _, calls = mac_install
    make_bundle(user_apps / "iTerm.app", desktop.MAC_APPS["iterm"])
    result = desktop.setup_desktop_app("iterm")
    assert result["status"] == "already_installed"
    assert result["path"] == str(user_apps / "iTerm.app")
    assert not any(command[0] == "download" for command in calls)


def test_mac_falls_back_to_user_applications(desktop, mac_install, monkeypatch):
    apps, user_apps, _, _ = mac_install
    real_access = desktop.os.access
    monkeypatch.setattr(desktop.os, "access", lambda p, mode: False if Path(p) == apps else real_access(p, mode))
    result = desktop.setup_desktop_app("iterm")
    assert result["path"] == str(user_apps / "iTerm.app")


def test_mac_never_overwrites_invalid_existing_app(desktop, mac_install):
    apps, _, _, calls = mac_install
    target = apps / "iTerm.app"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(RuntimeError, match="never overwritten"):
        desktop.setup_desktop_app("iterm")
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not calls


@pytest.mark.parametrize("failure", ["download", "signature", "copy", "timeout", "minimum_os"])
def test_mac_failures_clean_staging_and_do_not_claim_success(desktop, mac_install, monkeypatch, failure):
    apps, _, cache, calls = mac_install
    original = desktop._run

    def run(command, **kwargs):
        if failure == "signature" and command[0].endswith("codesign"):
            raise RuntimeError("signature rejected")
        if failure in {"copy", "timeout"} and command[0].endswith("ditto"):
            if failure == "timeout":
                raise subprocess.TimeoutExpired(command, 1)
            raise OSError("copy failed")
        return original(command, **kwargs)

    monkeypatch.setattr(desktop, "_run", run)
    if failure == "download":
        def download(*args):
            raise OSError("network unavailable")
        monkeypatch.setattr(desktop, "_download", download)
    if failure == "minimum_os":
        monkeypatch.setattr(desktop.platform, "mac_ver", lambda: ("13.0", (), ""))
    result = CliRunner().invoke(main, ["chrome"])
    assert result.exit_code != 0
    assert "Installation verified" not in result.output
    assert not list(apps.iterdir())
    assert not list(cache.iterdir())
    if failure != "download":
        assert calls[-1][1] == "detach"


@pytest.mark.parametrize("unsafe", ["../escape", "symlink"])
def test_iterm_rejects_unsafe_zip(desktop, mac_install, monkeypatch, unsafe):
    def download(url, archive):
        with zipfile.ZipFile(archive, "w") as bundle:
            if unsafe == "symlink":
                info = zipfile.ZipInfo("iTerm.app/link")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(info, "../../escape")
            else:
                bundle.writestr(unsafe, "unsafe")
    monkeypatch.setattr(desktop, "_download", download)
    with pytest.raises(RuntimeError, match="archive"):
        desktop.setup_desktop_app("iterm")


@pytest.mark.parametrize("already_installed", [True, False])
def test_windows_exact_package_is_verified(desktop, monkeypatch, already_installed):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Windows")
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "C:/Program Files/winget.exe")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert "--exact" in command and "Google.Chrome" in command
        assert "--accept-source-agreements" in command
        if command[1] == "list":
            present = already_installed or len(calls) > 1
            return subprocess.CompletedProcess(command, 0 if present else 1, "Google Chrome Google.Chrome 123" if present else "", "")
        assert "--no-upgrade" in command and "--silent" in command
        assert "--accept-package-agreements" in command
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(desktop, "_run", run)
    result = CliRunner().invoke(main, ["chrome", "--yes"])
    assert result.exit_code == 0, result.output
    assert "Installation verified" in result.output
    assert len(calls) == (1 if already_installed else 3)


def test_windows_missing_manager_and_failed_verification(desktop, monkeypatch):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Windows")
    monkeypatch.setattr(desktop.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="getwinget"):
        desktop.setup_desktop_app("chrome")
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "winget.exe")
    monkeypatch.setattr(desktop, "_run", lambda command, **k: subprocess.CompletedProcess(command, 0, "Other app", ""))
    with pytest.raises(RuntimeError, match="verification failed"):
        desktop.setup_desktop_app("chrome")


def test_linux_requires_explicit_privilege_before_download(desktop, monkeypatch):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Linux")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    monkeypatch.setattr(desktop, "_is_root", lambda: False)
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download before privilege check"))
    result = CliRunner().invoke(main, ["chrome"])
    assert result.exit_code != 0
    assert "chatup chrome --sudo" in result.output


def test_linux_installs_and_reads_browser_version(desktop, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Linux")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(desktop, "_is_root", lambda: False)
    monkeypatch.setattr(desktop, "_cache_dir", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/" + name if name in {"apt-get", "sudo"} or (name == "google-chrome-stable" and calls) else None)
    monkeypatch.setattr(desktop, "_download", lambda url, path: path.write_bytes(b"package"))

    def run(command, **kwargs):
        calls.append(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "Google Chrome 150.0.1.2\n", "")
        assert command[:4] == ["sudo", "apt-get", "install", "-y"]
        assert Path(command[-1]).is_file()
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(desktop, "_run", run)
    result = desktop.setup_desktop_app("chrome", sudo=True, yes=True)
    assert result["version"] == "150.0.1.2"
    assert result["status"] == "installed"
    assert desktop.setup_desktop_app("chrome")["status"] == "already_installed"
    assert len([c for c in calls if c[0] == "sudo"]) == 1


def test_subprocess_error_keeps_exit_code(desktop, monkeypatch):
    monkeypatch.setattr(desktop.subprocess, "run", lambda command, **k: subprocess.CompletedProcess(command, 7, "", "installer failed"))
    with pytest.raises(RuntimeError, match="exit 7.*installer failed"):
        desktop._run(["installer"])
