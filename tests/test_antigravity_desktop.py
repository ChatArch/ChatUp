"""Mocked native installation acceptance for Antigravity App."""
from pathlib import Path
import plistlib
import shutil
import subprocess

import pytest
from click.testing import CliRunner

from chatup.cli import main
from chatup.setup import desktop


@pytest.fixture
def mac(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(desktop.platform, "mac_ver", lambda: ("15.0", (), ""))
    root = tmp_path / "antigravity.noindex"
    apps, user_apps, cache = root / "Applications", root / "user/Applications", root / "cache"
    apps.mkdir(parents=True)
    cache.mkdir()
    monkeypatch.setattr(desktop, "_mac_app_dirs", lambda: (apps, user_apps))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: cache)
    return apps, user_apps, cache


def bundle(path, *, version="2.36.0", identifier="com.google.antigravity"):
    contents = path / "Contents"
    binary = contents / "MacOS/Antigravity"
    binary.parent.mkdir(parents=True)
    binary.write_text("fixture", encoding="utf-8")
    binary.chmod(0o755)
    (contents / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": identifier,
        "CFBundleExecutable": "Antigravity",
        "CFBundleShortVersionString": version,
        "LSMinimumSystemVersion": "13.0",
    }))


@pytest.mark.parametrize("machine,segment", [
    ("arm64", "darwin-arm"), ("aarch64", "darwin-arm"),
    ("x86_64", "darwin-x64"), ("amd64", "darwin-x64"),
])
def test_desktop_preview_is_offline_and_selects_app_not_ide(mac, monkeypatch, machine, segment):
    monkeypatch.setattr(desktop.platform, "machine", lambda: machine)
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not run processes"))
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("must not create cache"))
    result = CliRunner().invoke(main, ["antigravity", "desktop", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "/antigravity-public/antigravity-hub/2.36.0-" in result.output
    assert f"/{segment}/Antigravity.dmg" in result.output
    assert str(mac[0] / "Antigravity.app") in result.output
    assert "Dry run" in result.output and "Installation verified" not in result.output


@pytest.mark.parametrize("system,machine,version", [
    ("Windows", "AMD64", ""), ("Linux", "x86_64", ""),
    ("Darwin", "ppc", "15.0"), ("Darwin", "arm64", "12.7"),
])
def test_unsupported_desktop_fails_before_side_effects(mac, monkeypatch, system, machine, version):
    monkeypatch.setattr(desktop.platform, "system", lambda: system)
    monkeypatch.setattr(desktop.platform, "machine", lambda: machine)
    monkeypatch.setattr(desktop.platform, "mac_ver", lambda: (version, (), ""))
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("must not create cache"))
    result = CliRunner().invoke(main, ["antigravity", "desktop"])
    assert result.exit_code != 0
    assert "Error:" in result.output


@pytest.fixture
def installer(mac, monkeypatch):
    apps, _, cache = mac
    calls = []

    def download(url, path):
        calls.append(["download", url])
        path.write_bytes(b"dmg fixture")

    def run(command, **kwargs):
        calls.append(command)
        if command[0].endswith("hdiutil") and command[1] == "attach":
            bundle(Path(command[command.index("-mountpoint") + 1]) / "Antigravity.app")
        elif command[0].endswith("ditto"):
            assert {"--norsrc", "--noextattr", "--qtn"} <= set(command)
            shutil.copytree(command[-2], command[-1])
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(desktop, "_download", download)
    monkeypatch.setattr(desktop, "_run", run)
    return apps, cache, calls, run


def test_desktop_install_verifies_before_placement_then_reuses_newer_app(installer, monkeypatch):
    apps, cache, calls, run = installer

    def verify(command, **kwargs):
        if command[0].endswith("codesign"):
            assert {"--verify", "--deep", "--strict", "-R"} <= set(command)
            assert 'certificate leaf[subject.OU] = "EQHXZ8M8AV"' in command[-2]
            if Path(command[-1]).parent != apps:
                assert not (apps / "Antigravity.app").exists()
        return run(command, **kwargs)

    monkeypatch.setattr(desktop, "_run", verify)
    result = desktop.setup_desktop_app("antigravity")
    assert result["status"] == "installed" and result["verified"] is True
    assert result["version"] == "2.36.0"
    assert sum(c[0].endswith("spctl") for c in calls) == 2
    assert calls[-1][1] == "detach"
    assert not list(cache.iterdir())
    info_path = apps / "Antigravity.app/Contents/Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    info["CFBundleShortVersionString"] = "2.37.0"
    info_path.write_bytes(plistlib.dumps(info))
    calls.clear()
    repeated = CliRunner().invoke(main, ["antigravity", "desktop"])
    assert repeated.exit_code == 0, repeated.output
    assert "Already installed" in repeated.output and "2.37.0" in repeated.output
    assert all(c[0].endswith(("codesign", "spctl")) for c in calls)


@pytest.mark.parametrize("failure", ["codesign", "spctl", "ditto"])
def test_failed_desktop_staging_cleans_cache_without_placing_app(installer, monkeypatch, failure):
    apps, cache, calls, run = installer

    def reject(command, **kwargs):
        if command[0].endswith(failure):
            raise RuntimeError(f"fixture {failure} rejected")
        return run(command, **kwargs)

    monkeypatch.setattr(desktop, "_run", reject)
    result = CliRunner().invoke(main, ["antigravity", "desktop"])
    assert result.exit_code != 0 and f"{failure} rejected" in result.output
    assert not list(apps.iterdir()) and not list(cache.iterdir())
    assert calls[-1][1] == "detach"


def test_existing_ide_identity_is_preserved_and_rejected(mac, monkeypatch):
    apps, _, cache = mac
    target = apps / "Antigravity.app"
    bundle(target, identifier="com.google.antigravity.ide")
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not execute invalid bundle"))
    result = CliRunner().invoke(main, ["antigravity", "desktop"])
    assert result.exit_code != 0 and "bundle identity" in result.output
    assert target.is_dir() and not list(cache.iterdir())
