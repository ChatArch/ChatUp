"""CLI coverage for the documented official Gemini installation commands."""
import pytest
from click.testing import CliRunner

from chatup.commands.gemini import gemini_cli


def test_cli_offline_dry_run_shows_official_npm_package(monkeypatch):
    from chatup.setup import gemini

    monkeypatch.setattr(gemini.platform, "system", lambda: "Linux")
    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", lambda **k: pytest.fail("no runtime probes"))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("no npm"))
    result = CliRunner().invoke(gemini_cli, ["cli", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "npm install -g @google/gemini-cli" in result.output
    assert "Node.js >= 20" in result.output and "Dry run" in result.output
    assert "Installation verified" not in result.output
    assert "antigravity" not in result.output.lower() and "agy" not in result.output


@pytest.mark.parametrize("status,label", [("installed", "Installed"), ("already_installed", "Already installed")])
def test_cli_prints_verified_installation(monkeypatch, status, label):
    from chatup.setup import gemini

    monkeypatch.setattr(gemini, "setup_gemini_cli", lambda **k: {
        "status": status, "verified": True, "version": "0.71.1", "binary": "/npm/gemini.js",
    })
    result = CliRunner().invoke(gemini_cli, ["cli"])
    assert result.exit_code == 0, result.output
    assert f"{label}: Gemini CLI 0.71.1" in result.output
    assert "Installation verified" in result.output and "Run gemini" in result.output


def test_cli_errors_do_not_claim_installation(monkeypatch):
    from chatup.setup import gemini

    def fail(**kwargs):
        raise RuntimeError("npm installation failed")

    monkeypatch.setattr(gemini, "setup_gemini_cli", fail)
    result = CliRunner().invoke(gemini_cli, ["cli"])
    assert result.exit_code != 0 and "npm installation failed" in result.output
    assert "Installation verified" not in result.output


def test_desktop_uses_official_native_installer(monkeypatch):
    from chatup.commands import desktop

    calls = []
    monkeypatch.setattr(desktop, "_install", lambda app, **kwargs: calls.append((app, kwargs)))
    result = CliRunner().invoke(gemini_cli, ["desktop", "--dry-run", "--log-level", "DEBUG"])
    assert result.exit_code == 0
    assert calls == [("gemini", {"dry_run": True, "log_level": "DEBUG"})]


def test_group_help_exposes_both_official_surfaces():
    result = CliRunner().invoke(gemini_cli, ["--help"])
    assert result.exit_code == 0
    assert "cli" in result.output and "desktop" in result.output
