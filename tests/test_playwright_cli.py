from pathlib import Path

import click
from click.testing import CliRunner

import chatup.commands.playwright as command
from chatup.cli import main
from chatup.runtime.playwright import PlaywrightBrowserInstallation


def _installation(tmp_path: Path) -> PlaywrightBrowserInstallation:
    root = tmp_path / "1.61.1" / "chromium"
    return PlaywrightBrowserInstallation(
        kind="playwright",
        playwright_version="1.61.1",
        browser="chromium",
        browser_revision="1228",
        browser_version="149.0.7827.55",
        root_dir=root,
        package_dir=root / "package",
        browsers_dir=root / "browsers",
        binary_path=root / "browsers" / "chromium-1228" / "chrome",
        node_version="v22.1.0",
        installed_at="2026-08-04T00:00:00+00:00",
    )


def test_playwright_exposes_only_task_required_commands():
    group = main.commands["playwright"]
    assert isinstance(group, click.Group)
    assert set(group.commands) == {"install", "path", "doctor"}


def test_playwright_install_json(monkeypatch, tmp_path):
    installation = _installation(tmp_path)
    monkeypatch.setattr(command.backend, "install", lambda *_args, **_kwargs: installation)
    monkeypatch.setattr(
        command.backend,
        "doctor",
        lambda *_args, **_kwargs: {
            **installation.to_dict(),
            "status": "ready",
            "errors": [],
            "observed_version": "Google Chrome for Testing 149.0.7827.55",
        },
    )

    result = CliRunner().invoke(
        main,
        [
            "playwright",
            "install",
            "1.61.1",
            "--home",
            str(tmp_path),
            "--output",
            "json",
            "-I",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"browser_revision": "1228"' in result.output
    assert '"status": "ready"' in result.output


def test_playwright_path_prints_binary(monkeypatch, tmp_path):
    installation = _installation(tmp_path)
    monkeypatch.setattr(command.backend, "resolve", lambda *_args, **_kwargs: installation)

    result = CliRunner().invoke(
        main,
        ["playwright", "path", "1.61.1", "--home", str(tmp_path), "-I"],
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(installation.binary_path)


def test_playwright_missing_version_fails_non_interactively():
    result = CliRunner().invoke(main, ["playwright", "path", "-I"])

    assert result.exit_code != 0
    assert "version" in result.output.lower()


def test_playwright_doctor_returns_nonzero_when_unhealthy(monkeypatch, tmp_path):
    installation = _installation(tmp_path)
    monkeypatch.setattr(command.backend, "resolve", lambda *_args, **_kwargs: installation)
    monkeypatch.setattr(
        command.backend,
        "doctor",
        lambda *_args, **_kwargs: {
            **installation.to_dict(),
            "status": "unhealthy",
            "errors": ["execution_failed"],
            "observed_version": None,
        },
    )

    result = CliRunner().invoke(
        main,
        ["playwright", "doctor", "1.61.1", "--home", str(tmp_path), "-I"],
    )
    assert result.exit_code != 0
    assert "execution_failed" in result.output
