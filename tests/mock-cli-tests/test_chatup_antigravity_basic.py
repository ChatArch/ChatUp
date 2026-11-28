"""CLI coverage for the documented Antigravity installation surfaces."""
import pytest
from click.testing import CliRunner

from chatup.commands.antigravity import antigravity_cli


def test_cli_dry_run_is_an_offline_preview(monkeypatch, tmp_path):
    from chatup.setup import antigravity

    monkeypatch.setattr(antigravity.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(antigravity.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(antigravity, "_run", lambda *a, **k: pytest.fail("no processes"))
    monkeypatch.setattr(antigravity, "_download_installer", lambda *a: pytest.fail("no downloads"))
    monkeypatch.setattr(antigravity, "_cache_dir", lambda: pytest.fail("no cache creation"))
    target = tmp_path / "custom bin"
    result = CliRunner().invoke(antigravity_cli, ["cli", "--dry-run", "--install-dir", str(target)])
    assert result.exit_code == 0, result.output
    assert "https://antigravity.google/cli/install.sh" in result.output
    assert str(target / "agy") in result.output
    assert "Dry run" in result.output and "Installation verified" not in result.output
    assert not target.exists()


@pytest.mark.parametrize("status,label", [("installed", "Installed"), ("already_installed", "Already installed")])
def test_cli_prints_only_verified_install_success(monkeypatch, status, label):
    from chatup.setup import antigravity

    monkeypatch.setattr(antigravity, "setup_antigravity_cli", lambda **k: {
        "status": status, "binary": "/example/agy", "version": "1.5.18", "verified": True,
    })
    result = CliRunner().invoke(antigravity_cli, ["cli"])
    assert result.exit_code == 0, result.output
    assert f"{label}: Antigravity CLI 1.5.18" in result.output
    assert "/example/agy" in result.output and "Installation verified" in result.output


def test_cli_failure_does_not_print_install_success(monkeypatch):
    from chatup.setup import antigravity

    def fail(**kwargs):
        raise RuntimeError("official installer failed")

    monkeypatch.setattr(antigravity, "setup_antigravity_cli", fail)
    result = CliRunner().invoke(antigravity_cli, ["cli"])
    assert result.exit_code != 0
    assert "official installer failed" in result.output
    assert "Installation verified" not in result.output


def test_desktop_delegates_to_signed_native_app_installer(monkeypatch):
    from chatup.commands import desktop

    calls = []
    monkeypatch.setattr(desktop, "_install", lambda app, **kwargs: calls.append((app, kwargs)))
    result = CliRunner().invoke(antigravity_cli, ["desktop", "--dry-run", "--log-level", "DEBUG"])
    assert result.exit_code == 0, result.output
    assert calls == [("antigravity", {"dry_run": True, "log_level": "DEBUG"})]


def test_group_exposes_cli_and_desktop_help():
    result = CliRunner().invoke(antigravity_cli, ["--help"])
    assert result.exit_code == 0
    assert "cli" in result.output and "desktop" in result.output
