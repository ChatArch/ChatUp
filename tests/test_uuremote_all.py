"""UU Remote and OS-filtered batch setup CLI contracts."""
import hashlib
import importlib
from pathlib import Path
import subprocess

import click
import pytest
from click.testing import CliRunner

from chatup.cli import main


def test_uuremote_plan_is_read_only_and_platform_bound(monkeypatch):
    desktop = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(desktop.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(desktop.platform, "mac_ver", lambda: ("11.0", (), ""))
    monkeypatch.setattr(desktop, "_run", lambda *a, **kw: pytest.fail("ran subprocess"))
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("downloaded"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("made cache"))
    result = CliRunner().invoke(main, ["uuremote", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "macos_pkg" not in result.output
    assert "e347e1dfd57566934ae881f58f09fdd6ab1afae7f521cbfff3aa27a46a6c9560" in result.output
    assert "/Applications/UURemote.app" in result.output
    for system, version in [("Windows", ""), ("Linux", ""), ("Darwin", "10.15")]:
        monkeypatch.setattr(desktop.platform, "system", lambda: system)
        monkeypatch.setattr(desktop.platform, "mac_ver", lambda: (version, (), ""))
        unsupported = CliRunner().invoke(main, ["uuremote", "--dry-run"])
        assert unsupported.exit_code != 0
        assert "macOS" in unsupported.output


@pytest.fixture
def pkg_install(monkeypatch, tmp_path):
    desktop = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(desktop.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(desktop.platform, "mac_ver", lambda: ("15.0", (), ""))
    monkeypatch.setattr(desktop, "_mac_app_dirs", lambda: (tmp_path / "Applications", tmp_path / "user"))
    monkeypatch.setattr(desktop, "_uuremote_conflicts", lambda: [])
    monkeypatch.setattr(desktop, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(desktop, "_is_root", lambda: False)
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/sudo" if name == "sudo" else None)
    payload = b"official fixture"
    monkeypatch.setitem(desktop.MAC_APPS, "uuremote", {
        **desktop.MAC_APPS["uuremote"], "sha256": hashlib.sha256(payload).hexdigest(),
    })
    commands = []
    target = tmp_path / "Applications/UURemote.app"
    monkeypatch.setattr(desktop, "_download", lambda url, path: path.write_bytes(payload))
    monkeypatch.setattr(desktop, "_mac_bundle", lambda plan, path: {
        "path": str(path), "version": "4.46.0", "binary": str(path / "Contents/MacOS/UURemote"),
    })

    def run(command, **kwargs):
        commands.append(command)
        if "--pkg-info" in command:
            return subprocess.CompletedProcess(command, 1, "", "not installed")
        if "--check-signature" in command:
            return subprocess.CompletedProcess(command, 0,
                "Developer ID Installer: Hangzhou Bobo Technology Co Ltd (PU9BNSBJW7)\n"
                "Notarization: trusted by the Apple notary service", "")
        if command[0] == "sudo":
            target.mkdir(parents=True)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(desktop, "_run", run)
    return desktop, target, commands


def test_uuremote_requires_explicit_sudo_and_verifies_pkg(pkg_install):
    desktop, target, commands = pkg_install
    denied = CliRunner().invoke(main, ["uuremote"])
    assert denied.exit_code != 0 and "--sudo" in denied.output
    assert not commands and not target.exists()
    result = CliRunner().invoke(main, ["uuremote", "--sudo"])
    assert result.exit_code == 0, result.output
    assert [cmd[1] for cmd in commands[:3]] == ["--pkg-info", "--check-signature", "--assess"]
    assert commands[-1][0:3] == ["sudo", "/usr/sbin/installer", "-pkg"]
    assert not list(Path(desktop._cache_dir()).glob("uuremote-*"))
    commands.clear()
    again = CliRunner().invoke(main, ["uuremote"])
    assert again.exit_code == 0 and "Already installed" in again.output
    assert not commands


@pytest.mark.parametrize("failure", ["checksum", "signature", "notarization", "conflict", "receipt"])
def test_uuremote_fails_closed_without_install(pkg_install, monkeypatch, tmp_path, failure):
    desktop, target, commands = pkg_install
    if failure == "checksum":
        monkeypatch.setitem(desktop.MAC_APPS, "uuremote", {**desktop.MAC_APPS["uuremote"], "sha256": "0" * 64})
    if failure == "conflict":
        conflict = tmp_path / "prior-cli"
        conflict.touch()
        monkeypatch.setattr(desktop, "_uuremote_conflicts", lambda: [conflict])
    previous = desktop._run

    def run(command, **kwargs):
        if failure == "receipt" and "--pkg-info" in command:
            return subprocess.CompletedProcess(command, 0, "receipt", "")
        if failure in {"signature", "notarization"} and "--check-signature" in command:
            return subprocess.CompletedProcess(command, 0, "other publisher" if failure == "signature" else
                "Developer ID Installer: Hangzhou Bobo Technology Co Ltd (PU9BNSBJW7)", "")
        return previous(command, **kwargs)

    monkeypatch.setattr(desktop, "_run", run)
    result = CliRunner().invoke(main, ["uuremote", "--sudo"])
    assert result.exit_code != 0
    assert not target.exists()
    assert not any(command[0] == "sudo" for command in commands)
    assert not list(tmp_path.glob("uuremote-*"))


@pytest.mark.parametrize("system,machine,expected,missing", [
    ("Darwin", "arm64", "uuremote", None),
    ("Darwin", "x86_64", "uuremote", "blender"),
    ("Windows", "AMD64", "snipaste", "uuremote"),
    ("Linux", "x86_64", "chrome", "snipaste"),
])
def test_all_filters_by_host(monkeypatch, system, machine, expected, missing):
    batch = importlib.import_module("chatup.commands.all")
    desktop = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(batch.platform, "system", lambda: system)
    monkeypatch.setattr(desktop.platform, "machine", lambda: machine)
    monkeypatch.setattr(desktop.platform, "mac_ver", lambda: ("15.0", (), ""))
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    available = batch.supported_items()
    assert expected in available
    if missing:
        assert missing not in available
    assert {"uv", "nodejs"} <= set(available)


def test_all_requires_selection_or_tty_and_empty_selection_is_safe(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "nodejs": "Node.js"})
    denied = CliRunner().invoke(main, ["all", "-I"])
    assert denied.exit_code != 0 and "--only" in denied.output
    monkeypatch.setattr(batch, "resolve_interactive_mode", lambda *a, **k: (None, True, False, True, True))
    monkeypatch.setattr(batch, "ask_checkbox", lambda *a, **k: [])
    empty = CliRunner().invoke(main, ["all"])
    assert empty.exit_code == 0 and "nothing changed" in empty.output


def test_all_checkbox_shows_only_supported_items(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "chrome": "Chrome"})
    monkeypatch.setattr(batch, "resolve_interactive_mode", lambda *a, **k: (None, True, False, True, True))
    seen = []

    def select(message, *, choices, default_values, instruction):
        seen.append((message, [choice.value for choice in choices], default_values))
        return []

    monkeypatch.setattr(batch, "ask_checkbox", select)
    result = CliRunner().invoke(main, ["all"])
    assert result.exit_code == 0, result.output
    assert seen == [("Select tools to set up", ["uv", "chrome"], [])]


def test_all_executes_only_selected_and_reports_partial_failure(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"chrome": "Chrome", "snipaste": "Snipaste"})
    called = []
    def chrome(**kwargs):
        called.append(("chrome", kwargs))
        raise click.ClickException("simulated failure")
    def snipaste(**kwargs):
        called.append(("snipaste", kwargs))
    monkeypatch.setitem(main.commands, "chrome", click.Command("chrome", callback=chrome))
    monkeypatch.setitem(main.commands, "snipaste", click.Command("snipaste", callback=snipaste))
    invalid = CliRunner().invoke(main, ["all", "--only", "uuremote", "-I"])
    assert invalid.exit_code != 0 and "Unsupported" in invalid.output
    assert not called
    result = CliRunner().invoke(main, ["all", "--only", "chrome", "--only", "snipaste", "--only", "chrome", "-I"])
    assert result.exit_code != 0 and "chrome" in result.output
    assert [name for name, _ in called] == ["chrome", "snipaste"]
    assert called[0][1]["sudo"] is False
    assert called[1][1]["yes"] is False


def test_all_invokes_base_runtime_commands_with_defaults(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "nodejs": "Node.js"})
    calls = []
    monkeypatch.setitem(main.commands, "uv", click.Command("uv", callback=lambda **kw: calls.append(("uv", kw))))
    monkeypatch.setitem(main.commands, "nodejs", click.Command("nodejs", callback=lambda **kw: calls.append(("nodejs", kw))))
    result = CliRunner().invoke(main, ["all", "--only", "uv", "--only", "nodejs", "-I"])
    assert result.exit_code == 0, result.output
    assert calls == [("uv", {}), ("nodejs", {"interactive": False})]


def test_all_dry_run_does_not_invoke_installers(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "uuremote": "UU Remote"})
    monkeypatch.setattr(batch, "plan_desktop_install", lambda *a, **k: {"method": "macos_pkg", "path": "/Applications/UURemote.app"})
    result = CliRunner().invoke(main, ["all", "--only", "uv", "--only", "uuremote", "--dry-run", "-I"])
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output and "macos_pkg" in result.output
