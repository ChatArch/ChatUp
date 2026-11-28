"""Gemini remains independently selectable from Antigravity."""
import importlib

import pytest
from click.testing import CliRunner

from chatup.cli import main


@pytest.mark.parametrize("system,machine,expected", [
    ("Darwin", "arm64", {"gemini cli", "gemini desktop"}),
    ("Darwin", "x86_64", {"gemini cli"}),
    ("Linux", "x86_64", {"gemini cli"}),
    ("Windows", "AMD64", {"gemini cli"}),
])
def test_batch_filters_gemini_surfaces(monkeypatch, system, machine, expected):
    batch = importlib.import_module("chatup.commands.all")
    monkeypatch.setattr(batch.platform, "system", lambda: system)
    monkeypatch.setattr(batch.platform, "machine", lambda: machine)
    monkeypatch.setattr(batch.platform, "mac_ver", lambda: ("15.0", (), ""))
    paths = {path for path in batch.supported_items() if path.startswith("gemini")}
    assert paths == expected


def test_selecting_gemini_does_not_invoke_antigravity(monkeypatch):
    batch = importlib.import_module("chatup.commands.all")
    gemini = importlib.import_module("chatup.setup.gemini")
    antigravity = importlib.import_module("chatup.setup.antigravity")
    monkeypatch.setattr(batch, "supported_items", lambda: {"gemini cli": "Gemini CLI"})
    monkeypatch.setattr(antigravity, "setup_antigravity_cli", lambda **kw: pytest.fail("wrong product"))
    calls = []

    def install(**kwargs):
        calls.append(kwargs)
        return {"status": "already_installed", "app": "Gemini CLI", "version": "0.71.1", "binary": "/user/bin/gemini"}

    monkeypatch.setattr(gemini, "setup_gemini_cli", install)
    args = ["all", "--only", "gemini cli", "-I"]
    preview = CliRunner().invoke(main, [*args, "--dry-run"])
    assert preview.exit_code == 0, preview.output
    assert "Would run: chatup gemini cli" in preview.output
    assert calls == []
    applied = CliRunner().invoke(main, args)
    assert applied.exit_code == 0, applied.output
    assert len(calls) == 1
    assert "0.71.1" in applied.output
