import importlib
from pathlib import Path
import subprocess

import pytest
from click.testing import CliRunner

from chatup.cli import main


def desktop(monkeypatch, system="Darwin"):
    module = importlib.import_module("chatup.setup.chatgpt")
    monkeypatch.setattr(module.platform, "system", lambda: system)
    return module


def test_chatgpt_help_distinguishes_desktop_from_codex_cli():
    result = CliRunner().invoke(main, ["chatgpt", "--help"])
    assert result.exit_code == 0, result.output
    for text in ("desktop", "Codex", "--dry-run", "--yes"):
        assert text in result.output
    codex = CliRunner().invoke(main, ["codex", "--help"])
    assert codex.exit_code == 0
    assert "--install-only" in codex.output
    assert "--api-key" in codex.output


@pytest.mark.parametrize("flag", ["--tree", "--tree-brief"])
def test_chatgpt_in_real_tree(flag):
    result = CliRunner().invoke(main, [flag])
    assert result.exit_code == 0
    assert "chatgpt" in result.output


def test_macos_plan_uses_current_official_cask(monkeypatch):
    plan = desktop(monkeypatch).plan_chatgpt_install()
    assert plan["command"] == ["brew", "install", "--cask", "homebrew/cask/chatgpt"]
    assert plan["verify_command"] == ["brew", "list", "--cask", "--versions", "homebrew/cask/chatgpt"]
    assert plan["package"] == "homebrew/cask/chatgpt"
    assert plan["app"] == "ChatGPT (includes Codex)"


@pytest.mark.parametrize("yes", [False, True])
def test_windows_plan_pins_official_store_product(monkeypatch, yes):
    plan = desktop(monkeypatch, "Windows").plan_chatgpt_install(yes=yes)
    assert plan["command"][:8] == ["winget", "install", "--id", "9PLM9XGG6VKS", "--exact", "--source", "msstore", "--disable-interactivity"]
    assert ("--accept-package-agreements" in plan["command"]) is yes
    assert ("--accept-source-agreements" in plan["command"]) is yes
    assert ("--accept-source-agreements" in plan["verify_command"]) is yes
    assert "--accept-package-agreements" not in plan["verify_command"]
    assert "--no-upgrade" in plan["command"]
    assert "9NT1R1C2HH7J" not in str(plan)  # Classic, not the Codex-based desktop app


@pytest.mark.parametrize("system", ["Linux", "FreeBSD"])
def test_unautomated_platform_fails_without_subprocess(monkeypatch, system):
    module = desktop(monkeypatch, system)
    monkeypatch.setattr(module.shutil, "which", lambda _: pytest.fail("must fail before dependency lookup"))
    with pytest.raises(RuntimeError, match="macOS and Windows"):
        module.setup_chatgpt()
    result = CliRunner().invoke(main, ["chatgpt", "--dry-run"])
    assert result.exit_code != 0
    if system == "Linux":
        assert "https://learn.chatgpt.com/docs/linux/linux-app" in result.output


@pytest.mark.parametrize("system", ["Darwin", "Windows"])
def test_dry_run_has_no_install_or_dependency_side_effects(monkeypatch, system):
    module = desktop(monkeypatch, system)
    monkeypatch.setattr(module.shutil, "which", lambda _: pytest.fail("dry-run must not require a manager"))
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("dry-run must not execute anything"))
    result = module.setup_chatgpt(dry_run=True)
    assert result["status"] == "planned"
    assert result["verified"] is False
    cli = CliRunner().invoke(main, ["chatgpt", "--dry-run"])
    assert cli.exit_code == 0, cli.output
    assert "ChatGPT" in cli.output and "Codex" in cli.output
    assert "install" in cli.output
    assert "安装完成" not in cli.output


@pytest.mark.parametrize("system, manager", [("Darwin", "brew"), ("Windows", "winget")])
def test_missing_manager_is_actionable(monkeypatch, system, manager):
    module = desktop(monkeypatch, system)
    monkeypatch.setattr(module.shutil, "which", lambda _: None)
    result = CliRunner().invoke(main, ["chatgpt"])
    assert result.exit_code != 0
    assert manager in result.output
    assert "https://" in result.output


@pytest.mark.parametrize("system, listing", [("Darwin", "chatgpt 26.908.70816\n"), ("Windows", "ChatGPT 9PLM9XGG6VKS msstore\n")])
@pytest.mark.parametrize("already_installed", [False, True])
def test_installer_uses_resolved_manager_and_reads_back(monkeypatch, system, listing, already_installed):
    module = desktop(monkeypatch, system)
    calls = []
    executable = "/package manager/manager"
    monkeypatch.setattr(module.shutil, "which", lambda _: executable)

    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert args[0] == executable
        assert kwargs.get("shell", False) is False
        assert kwargs["timeout"] > 0
        if args[1] == "list":
            present = already_installed or len(calls) > 1
            return subprocess.CompletedProcess(args, 0 if present else 1, listing if present else "", "")
        assert args[1] == "install"
        assert not kwargs.get("capture_output", False)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(module.subprocess, "run", run)
    result = module.setup_chatgpt(yes=True)
    assert result["status"] == ("already_installed" if already_installed else "installed")
    assert result["verified"] is True
    assert [a[1] for a, _ in calls] == (["list"] if already_installed else ["list", "install", "list"])


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "oserror", "missing_after_install"])
def test_install_errors_do_not_report_success(monkeypatch, failure):
    module = desktop(monkeypatch)
    monkeypatch.setattr(module.shutil, "which", lambda _: "/brew")

    def run(args, **kwargs):
        if args[1] == "list":
            return subprocess.CompletedProcess(args, 1, "", "")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if failure == "oserror":
            raise OSError("cannot execute")
        return subprocess.CompletedProcess(args, 7 if failure == "nonzero" else 0)

    monkeypatch.setattr(module.subprocess, "run", run)
    result = CliRunner().invoke(main, ["chatgpt"])
    assert result.exit_code != 0
    assert "安装完成" not in result.output
    assert "Error:" in result.output


def test_legacy_chatgpt_cask_is_not_reported_as_new_app(monkeypatch):
    module = desktop(monkeypatch)
    monkeypatch.setattr(module.shutil, "which", lambda _: "/brew")

    def run(args, **kwargs):
        assert args[1] == "list", "must not migrate or upgrade a Classic installation"
        return subprocess.CompletedProcess(args, 0, "chatgpt 1.2026.182\n", "")

    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="Classic"):
        module.setup_chatgpt()


def test_empty_brew_listing_does_not_count_as_installed(monkeypatch):
    module = desktop(monkeypatch)
    monkeypatch.setattr(module.shutil, "which", lambda _: "/brew")
    monkeypatch.setattr(module.subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    with pytest.raises(RuntimeError, match="verification"):
        module.setup_chatgpt()


@pytest.mark.parametrize("relative", [
    "README.md", "README.en.md", "docs/commands.md", "docs/commands.en.md",
    "docs/cli-tree.md", "docs/cli-tree.en.md", "docs/capability-map.md",
    "docs/capability-map.en.md",
])
def test_desktop_command_is_documented(relative):
    text = (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")
    assert "chatup chatgpt" in text
    assert "Codex" in text


def test_cli_yes_is_forwarded(monkeypatch):
    import chatup.setup.elements as elements
    calls = []

    def setup(**kwargs):
        calls.append(kwargs)
        return {"status": "already_installed", "app": "ChatGPT (includes Codex)", "command": ["brew", "install"], "platform": "Darwin", "verified": True}

    monkeypatch.setattr(elements, "setup_chatgpt", setup)
    result = CliRunner().invoke(main, ["chatgpt", "--dry-run", "--yes"])
    assert result.exit_code == 0, result.output
    assert calls == [{"dry_run": True, "yes": True}]
