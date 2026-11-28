"""Antigravity leaf selection through the complete tool installer."""
import importlib

import pytest
from click.testing import CliRunner

from chatup.cli import main


@pytest.mark.parametrize("system,machine,expected", [
    ("Darwin", "arm64", {"antigravity cli", "antigravity desktop"}),
    ("Darwin", "x86_64", {"antigravity cli", "antigravity desktop"}),
    ("Linux", "x86_64", {"antigravity cli"}),
    ("Windows", "AMD64", {"antigravity cli"}),
    ("Linux", "i686", set()),
])
def test_batch_filters_antigravity_surfaces(monkeypatch, system, machine, expected):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch.platform, "system", lambda: system)
    monkeypatch.setattr(batch.platform, "machine", lambda: machine)
    monkeypatch.setattr(batch.platform, "mac_ver", lambda: ("15.0", (), ""))
    paths = {path for path in batch.supported_items() if path.startswith("antigravity")}
    assert paths == expected


def test_batch_antigravity_preview_and_selected_install(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    cli = importlib.import_module("chatup.setup.antigravity")
    desktop = importlib.import_module("chatup.setup.desktop")
    paths = ("antigravity cli", "antigravity desktop")
    monkeypatch.setattr(batch, "supported_items", lambda: dict.fromkeys(paths, "Antigravity"))
    calls = []

    def install_cli(**kwargs):
        calls.append(("cli", kwargs))
        return {"status": "already_installed", "version": "1.5.18", "binary": "/user/bin/agy"}

    def install_desktop(app, **kwargs):
        calls.append((app, kwargs))
        return {"status": "already_installed", "app": "Antigravity App", "version": "2.36.0"}

    monkeypatch.setattr(cli, "setup_antigravity_cli", install_cli)
    monkeypatch.setattr(desktop, "setup_desktop_app", install_desktop)
    args = ["all", "--only", paths[0], "--only", paths[1], "-I"]
    preview = CliRunner().invoke(main, [*args, "--dry-run"])
    assert preview.exit_code == 0, preview.output
    assert "Would run: chatup antigravity cli" in preview.output
    assert "Would run: chatup antigravity desktop" in preview.output
    assert calls == []
    applied = CliRunner().invoke(main, args)
    assert applied.exit_code == 0, applied.output
    assert [call[0] for call in calls] == ["cli", "antigravity"]
    assert "Selected ChatUp actions completed." in applied.output
