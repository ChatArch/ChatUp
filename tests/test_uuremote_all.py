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
    assert desktop.plan_desktop_install("uuremote")["path"] in result.output
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
    ("Darwin", "arm64", "uuremote", "glance"),
    ("Darwin", "x86_64", "macos", "mysql"),
    ("Windows", "AMD64", "chatgpt", "uuremote"),
    ("Linux", "x86_64", "mysql", "snipaste"),
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
    assert {"uv", "nodejs", "workspace", "codex", "hermes", "discourse", "zulip",
            "nginx", "chrome-for-testing install", "chromedriver list", "playwright doctor"} <= set(available)
    assert "all" not in available
    assert "chrome-for-testing" not in available


def test_all_registered_leaf_coverage_and_read_only_listing(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(batch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(batch.platform, "mac_ver", lambda: ("15.0", (), ""))
    expected = {
        path for path in batch._registered_leaves()
        if batch._supported(path, "Darwin", "arm64")
    }
    assert set(batch.supported_items()) == expected
    assert len(expected) > 35
    listing = CliRunner().invoke(main, ["all", "--list", "-I"])
    assert listing.exit_code == 0, listing.output
    assert {line.split(" - ", 1)[0] for line in listing.output.splitlines()} == expected


def test_all_linux_computer_use_requires_supported_distribution(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch.platform, "system", lambda: "Linux")
    monkeypatch.setattr(batch.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(batch.platform, "freedesktop_os_release", lambda: {"ID": "ubuntu"})
    assert "computer-use" in batch.supported_items()
    monkeypatch.setattr(batch.platform, "freedesktop_os_release", lambda: {"ID": "fedora"})
    assert "computer-use" not in batch.supported_items()


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
    assert seen == [("Select ChatUp actions to run", ["uv", "chrome"], [])]


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
    assert invalid.exit_code != 0 and "unsupported" in invalid.output
    assert not called
    result = CliRunner().invoke(main, ["all", "--only", "chrome", "--only", "snipaste", "--only", "chrome", "-I"])
    assert result.exit_code != 0 and "chrome" in result.output
    assert [name for name, _ in called] == ["chrome", "snipaste"]
    assert called[0][1] == {}
    assert called[1][1] == {}


def test_all_invokes_base_runtime_commands_with_defaults(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "nodejs": "Node.js"})
    calls = []
    monkeypatch.setitem(main.commands, "uv", click.Command("uv", callback=lambda **kw: calls.append(("uv", kw))))
    monkeypatch.setitem(main.commands, "nodejs", click.Command("nodejs", callback=lambda **kw: calls.append(("nodejs", kw))))
    result = CliRunner().invoke(main, ["all", "--only", "uv", "--only", "nodejs", "-I"])
    assert result.exit_code == 0, result.output
    assert calls == [("uv", {}), ("nodejs", {})]


def test_all_dry_run_does_not_invoke_installers(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"uv": "uv", "uuremote": "UU Remote"})
    result = CliRunner().invoke(main, ["all", "--only", "uv", "--only", "uuremote", "--dry-run", "-I"])
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output and "Would run: chatup uuremote" in result.output


def test_all_group_leaf_dispatch_uses_registered_command(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"playwright doctor": "Playwright doctor"})
    called = []
    group = click.Group("playwright")
    group.add_command(click.Command("doctor", callback=lambda: called.append("doctor")))
    monkeypatch.setitem(main.commands, "playwright", group)
    result = CliRunner().invoke(main, ["all", "--only", "playwright doctor", "-I"])
    assert result.exit_code == 0, result.output
    assert called == ["doctor"]


def test_all_never_forwards_yes_to_destructive_leaf(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"chromedriver remove": "Remove ChromeDriver"})
    called = []
    group = click.Group("chromedriver")
    group.add_command(click.Command("remove", callback=lambda: called.append("remove")))
    monkeypatch.setitem(main.commands, "chromedriver", group)
    result = CliRunner().invoke(main, ["all", "--only", "chromedriver remove", "--yes", "-I"])
    assert result.exit_code == 0, result.output
    assert called == ["remove"]


def test_all_preserves_platform_specific_service_and_interaction_options(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch.platform, "system", lambda: "Windows")
    called = []

    @click.command("nginx")
    @click.option("--service/--no-service", default=True)
    def nginx(service):
        called.append(("nginx", service))

    @click.command("nodejs")
    @click.option("--interactive/--no-interactive", "-i/-I", default=None)
    def nodejs(interactive):
        called.append(("nodejs", interactive))

    monkeypatch.setitem(main.commands, "nginx", nginx)
    monkeypatch.setitem(main.commands, "nodejs", nodejs)
    monkeypatch.setattr(batch, "supported_items", lambda: {"nginx": "NGINX", "nodejs": "Node.js"})
    result = CliRunner().invoke(main, ["all", "--only", "nginx", "--only", "nodejs", "-I"])
    assert result.exit_code == 0, result.output
    assert called == [("nginx", False), ("nodejs", False)]


def test_all_group_with_missing_required_version_does_not_run_next_action(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch, "supported_items", lambda: {"playwright doctor": "Doctor", "doctor": "Doctor CLI"})
    called = []
    group = click.Group("playwright")
    group.add_command(click.Command("doctor", params=[click.Argument(["version"])],
                                    callback=lambda version: called.append(("playwright", version))))
    monkeypatch.setitem(main.commands, "playwright", group)
    monkeypatch.setitem(main.commands, "doctor", click.Command("doctor", callback=lambda: called.append("doctor")))
    result = CliRunner().invoke(main, ["all", "--only", "playwright doctor", "--only", "doctor", "-I"])
    assert result.exit_code != 0
    assert "playwright doctor" in result.output
    assert called == ["doctor"]
