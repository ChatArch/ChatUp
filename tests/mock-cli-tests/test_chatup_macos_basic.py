import importlib

import click
from click.testing import CliRunner
import pytest

from chatup.cli import main


@pytest.fixture
def macos(monkeypatch):
    command = importlib.import_module("chatup.commands.macos")
    policy = importlib.import_module("chatup.interaction.policy")
    monkeypatch.setattr(command.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(policy, "is_interactive_available", lambda: False)
    monkeypatch.delenv("CHATARCH_AUTO_PROMPT", raising=False)
    calls = []
    monkeypatch.setattr(command, "_install", lambda app, **kwargs: calls.append((app, kwargs)))
    return command, policy, calls


@pytest.mark.parametrize("args", [[], ["-I"], ["--dry-run"]])
def test_default_selection_is_all_three_without_a_tty(macos, args):
    _, _, calls = macos
    result = CliRunner().invoke(main, ["macos", *args])
    assert result.exit_code == 0, result.output
    assert [app for app, _ in calls] == ["snipaste", "iterm", "chrome"]
    assert "Selected apps: Snipaste, iTerm2, Google Chrome" in result.output
    assert all(options["dry_run"] == ("--dry-run" in args) for _, options in calls)


def test_explicit_subset_is_deduplicated_without_prompt(macos, monkeypatch):
    command, policy, calls = macos
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    monkeypatch.setattr(command, "ask_checkbox", lambda *a, **k: pytest.fail("explicit apps must not prompt"))
    result = CliRunner().invoke(main, ["macos", "--app", "snipaste", "--app", "chrome", "--app", "snipaste", "--log-level", "DEBUG"])
    assert result.exit_code == 0, result.output
    assert [app for app, _ in calls] == ["snipaste", "chrome"]
    assert all(options["log_level"] == "DEBUG" for _, options in calls)


@pytest.mark.parametrize("selection", [["snipaste"], ["iterm", "chrome"], []])
def test_tty_checkboxes_default_to_all_and_respect_deselection(macos, monkeypatch, selection):
    command, policy, calls = macos
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)

    def choose(message, **kwargs):
        assert kwargs["default_values"] == ["snipaste", "iterm", "chrome"]
        assert len(kwargs["choices"]) == 3
        return selection

    monkeypatch.setattr(command, "ask_checkbox", choose)
    result = CliRunner().invoke(main, ["macos"])
    assert result.exit_code == 0, result.output
    assert [app for app, _ in calls] == selection
    if not selection:
        assert "nothing installed" in result.output


def test_forced_interactive_uses_explicit_selection_as_defaults(macos, monkeypatch):
    command, policy, calls = macos
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    monkeypatch.setenv("CHATARCH_AUTO_PROMPT", "0")

    def choose(message, **kwargs):
        assert kwargs["default_values"] == ["chrome"]
        return ["iterm"]

    monkeypatch.setattr(command, "ask_checkbox", choose)
    result = CliRunner().invoke(main, ["macos", "--app", "chrome", "-i", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert calls == [("iterm", {"dry_run": True, "log_level": "INFO"})]


@pytest.mark.parametrize("args,disabled", [(["-I"], False), (["--dry-run"], False), ([], True)])
def test_noninteractive_and_dry_run_skip_prompts_on_a_tty(macos, monkeypatch, args, disabled):
    command, policy, calls = macos
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    if disabled:
        monkeypatch.setenv("CHATARCH_AUTO_PROMPT", "0")
    monkeypatch.setattr(command, "ask_checkbox", lambda *a, **k: pytest.fail("must not prompt"))
    result = CliRunner().invoke(main, ["macos", *args])
    assert result.exit_code == 0, result.output
    assert len(calls) == 3


def test_forced_interactive_without_tty_does_not_install(macos):
    _, _, calls = macos
    result = CliRunner().invoke(main, ["macos", "-i"])
    assert result.exit_code != 0
    assert calls == []


def test_cancelled_selection_does_not_install(macos, monkeypatch):
    command, policy, calls = macos
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)

    def cancel(*args, **kwargs):
        raise click.Abort()

    monkeypatch.setattr(command, "ask_checkbox", cancel)
    result = CliRunner().invoke(main, ["macos"])
    assert result.exit_code != 0
    assert calls == []


@pytest.mark.parametrize("system", ["Linux", "Windows", "FreeBSD"])
def test_non_macos_rejected_before_prompts_or_install(macos, monkeypatch, system):
    command, _, calls = macos
    monkeypatch.setattr(command.platform, "system", lambda: system)
    monkeypatch.setattr(command, "ask_checkbox", lambda *a, **k: pytest.fail("must not prompt"))
    result = CliRunner().invoke(main, ["macos", "--app", "chrome"])
    assert result.exit_code != 0
    assert "macOS only" in result.output
    assert not calls


def test_invalid_app_is_rejected(macos):
    _, _, calls = macos
    result = CliRunner().invoke(main, ["macos", "--app", "unknown"])
    assert result.exit_code != 0
    assert not calls


def test_install_failure_stops_remaining_apps(macos, monkeypatch):
    command, _, calls = macos

    def install(app, **kwargs):
        calls.append(app)
        if app == "iterm":
            raise click.ClickException("signature verification failed")

    monkeypatch.setattr(command, "_install", install)
    result = CliRunner().invoke(main, ["macos", "-I"])
    assert result.exit_code != 0
    assert "signature verification failed" in result.output
    assert calls == ["snipaste", "iterm"]


def test_real_dry_run_does_not_execute_or_download(monkeypatch):
    desktop = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(desktop.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(desktop, "_download", lambda *a: pytest.fail("must not download"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("must not write"))
    result = CliRunner().invoke(main, ["macos", "--dry-run"])
    assert result.exit_code == 0, result.output
    for expected in ("Snipaste", "iTerm2", "Google Chrome", "https://dl.snipaste.com/mac"):
        assert expected in result.output
    assert result.output.count("Dry run:") == 3


@pytest.mark.parametrize("system", ["Linux", "Windows"])
def test_snipaste_does_not_fall_through_to_chrome_installer(monkeypatch, system):
    desktop = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(desktop.platform, "system", lambda: system)
    with pytest.raises(RuntimeError, match="Snipaste.*macOS only"):
        desktop.plan_desktop_install("snipaste")
