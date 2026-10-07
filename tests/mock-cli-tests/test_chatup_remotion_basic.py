import importlib
import json
from pathlib import Path

import click
from click.testing import CliRunner
import pytest

from chatup.cli import main


@pytest.fixture
def remotion(monkeypatch):
    module = importlib.import_module("chatup.setup.remotion")
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/tools/{name}")
    monkeypatch.setattr(
        module,
        "_runtime",
        lambda: (
            "/tools/node",
            {"node_bin": "/tools/node", "npm_bin": "/tools/npm", "source": "path"},
        ),
    )
    monkeypatch.setattr(module, "_find_browser", lambda value=None: None)
    monkeypatch.setattr(module, "npm_command_for_runtime", lambda runtime, args: ["/tools/npm", *args])
    monkeypatch.setattr(module, "node_runtime_env", lambda runtime: {})
    calls = []

    def run(command, *, cwd=None, **kwargs):
        calls.append((command, cwd))
        if command[1:] == ["--version"]:
            return "v24.21.0" if command[0].endswith("node") else "11.19.0"
        if command[1] == "ci":
            (cwd / "node_modules").mkdir()
            return "installed"
        if command[1] == "ls":
            return json.dumps({"dependencies": {
                name: {"version": version} for name, version in module.DEPENDENCIES.items()
            }})
        pytest.fail(str(command))

    monkeypatch.setattr(module, "_run", run)
    return module, calls


def test_initializes_locked_project_and_reuses_user_edits(remotion, tmp_path):
    module, calls = remotion
    target = tmp_path / "video project"
    result = module.setup_remotion(target)
    assert result["status"] == "created"
    assert result["version"] == "4.0.530"
    assert (target / module.MARKER).is_file()
    assert (target / "package-lock.json").is_file()
    assert (target / ".gitignore").is_file()
    installs = [command for command, _ in calls if "ci" in command]
    assert len(installs) == 1
    assert {"--ignore-scripts", "--include=optional", "--no-audit", "--no-fund"} <= set(installs[0])
    source = target / "src" / "index.jsx"
    source.write_text("user edits", encoding="utf-8")
    calls.clear()
    assert module.setup_remotion(target)["status"] == "already_initialized"
    assert source.read_text() == "user edits"
    assert not any("ci" in command for command, _ in calls)
    assert not list(tmp_path.glob(".chatup-remotion-*"))


@pytest.mark.parametrize("kind", ["directory", "file", "invalid-marker", "symlink"])
def test_refuses_unmanaged_targets_without_writes(remotion, tmp_path, kind):
    module, calls = remotion
    target = tmp_path / "existing"
    if kind == "file":
        target.write_text("user file")
    elif kind == "symlink":
        try:
            target.symlink_to(tmp_path, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks unavailable")
    else:
        target.mkdir()
        if kind == "invalid-marker":
            (target / module.MARKER).write_text("{}")
    with pytest.raises(RuntimeError, match="refus|Refus|managed"):
        module.setup_remotion(target)
    assert not calls
    assert not list(tmp_path.glob(".chatup-remotion-*"))


def test_missing_runtime_fails_before_creating_target(remotion, monkeypatch, tmp_path):
    module, _ = remotion
    monkeypatch.setattr(
        module,
        "_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("Node.js >=20 and npm >=9 are required")),
    )
    target = tmp_path / "missing-parent" / "video"
    with pytest.raises(RuntimeError, match="Node|npm"):
        module.setup_remotion(target)
    assert not target.parent.exists()


def test_project_plan_normalizes_parent_segments(remotion, tmp_path):
    module, _ = remotion
    target = tmp_path / "video"
    module.setup_remotion(target)
    plan = module.plan_remotion_setup(tmp_path / "unused" / ".." / "video")
    assert plan["path"] == str(target)
    assert plan["managed"] is True


@pytest.mark.parametrize("node,npm", [("v18.11.0", "11.0.0"), ("v24.0.0", "8.0.0"), ("invalid", "11.0.0")])
def test_rejects_incompatible_runtime_before_writes(remotion, monkeypatch, tmp_path, node, npm):
    module, _ = remotion
    monkeypatch.setattr(
        module,
        "_runtime",
        lambda: (_ for _ in ()).throw(
            RuntimeError(f"Node.js >=20 and npm >=9 are required; found {node}/{npm}.")
        ),
    )
    target = tmp_path / "video"
    with pytest.raises(RuntimeError, match="Node|npm"):
        module.setup_remotion(target)
    assert not target.exists()


@pytest.mark.parametrize("failure", ["npm", "dependency-version", "destination-race"])
def test_failure_preserves_destination_and_cleans_staging(remotion, monkeypatch, tmp_path, failure):
    module, _ = remotion
    target = tmp_path / "video"
    original = module._run

    def run(command, **kwargs):
        if command[1] == "ci":
            if failure == "npm":
                raise RuntimeError("npm failed")
            if failure == "destination-race":
                target.mkdir()
                (target / "user.txt").write_text("keep")
        if command[1] == "ls" and failure == "dependency-version":
            return '{"dependencies": {}}'
        return original(command, **kwargs)

    monkeypatch.setattr(module, "_run", run)
    with pytest.raises(RuntimeError):
        module.setup_remotion(target)
    assert not list(tmp_path.glob(".chatup-remotion-*"))
    if failure == "destination-race":
        assert list(target.iterdir()) == [target / "user.txt"]
    else:
        assert not target.exists()


def test_dry_run_never_executes_or_creates(remotion, monkeypatch, tmp_path):
    module, calls = remotion
    monkeypatch.setattr(module, "_run", lambda *a, **k: pytest.fail("must not execute"))
    target = tmp_path / "absent" / "video"
    result = CliRunner().invoke(main, ["remotion", str(target), "--dry-run", "-I"])
    assert result.exit_code == 0, result.output
    assert "4.0.530" in result.output and "Dry run" in result.output
    assert not target.parent.exists()
    assert not calls


def test_explicit_browser_is_validated_and_detected(monkeypatch, tmp_path):
    module = importlib.import_module("chatup.setup.remotion")
    browser = tmp_path / "chrome"
    with pytest.raises(RuntimeError, match="browser|Browser"):
        module.plan_remotion_setup(tmp_path / "video", browser_executable=browser)
    browser.write_text("fixture")
    browser.chmod(0o755)
    assert module._find_browser(browser) == str(browser)
    monkeypatch.setattr(module.shutil, "which", lambda name: str(browser))
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    assert module._find_browser() == str(browser)


def test_missing_browser_has_guidance_without_downloading(remotion, tmp_path):
    _, calls = remotion
    result = CliRunner().invoke(main, ["remotion", str(tmp_path / "video"), "-I"])
    assert result.exit_code == 0, result.output
    assert "chatup chrome" in result.output
    assert all("browser" not in command[1:] for command, _ in calls)


@pytest.fixture
def interaction(monkeypatch):
    command = importlib.import_module("chatup.commands.remotion")
    policy = importlib.import_module("chatup.interaction.policy")
    monkeypatch.setattr(policy, "is_interactive_available", lambda: False)
    monkeypatch.delenv("CHATARCH_AUTO_PROMPT", raising=False)
    return command, policy


@pytest.mark.parametrize("args", [[], ["-I"], ["-i"]])
def test_missing_path_without_tty_fails_before_setup(remotion, interaction, args):
    _, calls = remotion
    result = CliRunner().invoke(main, ["remotion", *args])
    assert result.exit_code != 0
    assert not calls


def test_missing_path_prompts_with_consistent_default(remotion, interaction, monkeypatch, tmp_path):
    command, policy = interaction
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    target = tmp_path / "video"

    def ask(message, default):
        assert default == str(Path.cwd() / "remotion-video")
        return str(target)

    monkeypatch.setattr(command, "ask_path", ask)
    result = CliRunner().invoke(main, ["remotion"])
    assert result.exit_code == 0, result.output
    assert target.is_dir()


def test_cancelled_prompt_does_not_install(remotion, interaction, monkeypatch):
    command, policy = interaction
    _, calls = remotion
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)

    def cancel(*args, **kwargs):
        raise click.Abort()

    monkeypatch.setattr(command, "ask_path", cancel)
    result = CliRunner().invoke(main, ["remotion"])
    assert result.exit_code != 0
    assert not calls


def test_explicit_path_skips_prompt_but_force_uses_it(remotion, interaction, monkeypatch, tmp_path):
    command, policy = interaction
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    monkeypatch.setattr(command, "ask_path", lambda *a, **k: pytest.fail("must not prompt"))
    result = CliRunner().invoke(main, ["remotion", str(tmp_path / "video"), "--dry-run"])
    assert result.exit_code == 0, result.output
    monkeypatch.setattr(command, "ask_path", lambda *a, **k: str(tmp_path / "chosen"))
    result = CliRunner().invoke(main, ["remotion", str(tmp_path / "video"), "-i", "--dry-run"])
    assert result.exit_code == 0 and str(tmp_path / "chosen") in result.output


def test_disabled_auto_prompt_requires_path(remotion, interaction, monkeypatch):
    command, policy = interaction
    monkeypatch.setattr(policy, "is_interactive_available", lambda: True)
    monkeypatch.setenv("CHATARCH_AUTO_PROMPT", "0")
    monkeypatch.setattr(command, "ask_path", lambda *a, **k: pytest.fail("must not prompt"))
    result = CliRunner().invoke(main, ["remotion"])
    assert result.exit_code != 0
