"""Offline coverage of the Gemini CLI Node/npm installation workflow."""
import json
from pathlib import Path
import subprocess

import click
import pytest

from chatup.setup import gemini


@pytest.fixture
def setup(monkeypatch, tmp_path):
    runtime = {"node_bin": str(tmp_path / "node"), "source": "path", "node_major": 26}
    monkeypatch.setattr(gemini.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", lambda **k: runtime)
    monkeypatch.setattr(gemini, "node_runtime_env", lambda _: {"PATH": "runtime-bin", "TEST_RUNTIME": "selected"})
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: None)
    return runtime, tmp_path / "node_modules"


def package_fixture(root, *, version="0.71.1", binary="bundle/gemini.js", name=gemini.NPM_PACKAGE):
    package = root / "@google" / "gemini-cli"
    package.mkdir(parents=True, exist_ok=True)
    (package / "package.json").write_text(json.dumps({"name": name, "version": version, "bin": {"gemini": binary}}))
    entry = package / binary
    if not Path(binary).is_absolute() and ".." not in Path(binary).parts:
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("// Gemini CLI fixture")
    return entry


@pytest.mark.parametrize("system", ["Darwin", "Linux", "Windows"])
def test_dry_run_is_offline_and_does_not_probe_node_or_npm(setup, monkeypatch, system, tmp_path):
    monkeypatch.setattr(gemini.platform, "system", lambda: system)
    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", lambda **k: pytest.fail("no Node probes"))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("no npm processes"))
    monkeypatch.setattr(gemini.subprocess, "run", lambda *a, **k: pytest.fail("no processes"))
    result = gemini.setup_gemini_cli(dry_run=True)
    assert result["status"] == "planned" and result["verified"] is False
    assert result["command"] == ["npm", "install", "-g", "@google/gemini-cli"]
    assert result["minimum_node_major"] == 20
    assert not list(tmp_path.iterdir())


def test_unsupported_platform_fails_before_any_runtime_probe(setup, monkeypatch):
    monkeypatch.setattr(gemini.platform, "system", lambda: "FreeBSD")
    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", lambda **k: pytest.fail("no Node probes"))
    with pytest.raises(RuntimeError, match="does not support FreeBSD"):
        gemini.setup_gemini_cli()


@pytest.mark.parametrize("system", ["Darwin", "Linux", "Windows"])
def test_fresh_install_uses_shared_npm_and_verifies_with_selected_node(setup, monkeypatch, system):
    runtime, root = setup
    monkeypatch.setattr(gemini.platform, "system", lambda: system)
    npm_calls = []
    verify_calls = []
    ensured = []

    def ensure(**kwargs):
        ensured.append(kwargs)
        return runtime

    def npm(args):
        npm_calls.append(args)
        if args == ["root", "-g"]:
            return subprocess.CompletedProcess(args, 0, str(root), "")
        assert args == ["install", "-g", "@google/gemini-cli"]
        package_fixture(root)
        return subprocess.CompletedProcess(args, 0, "installed", "")

    def run(command, **kwargs):
        verify_calls.append(command)
        assert command == [runtime["node_bin"], str(root / "@google/gemini-cli/bundle/gemini.js"), "--version"]
        assert kwargs["env"] == {"PATH": "runtime-bin", "TEST_RUNTIME": "selected"}
        assert kwargs["timeout"] == 60
        assert not kwargs.get("shell")
        return subprocess.CompletedProcess(command, 0, "0.71.1\n", "")

    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(root / "@google/gemini-cli/bundle/gemini.js") if (root / "@google/gemini-cli/bundle/gemini.js").is_file() else None)
    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", ensure)
    monkeypatch.setattr(gemini, "run_npm_command", npm)
    monkeypatch.setattr(gemini.subprocess, "run", run)
    result = gemini.setup_gemini_cli()
    assert ensured == [{"min_major": 20, "interactive": False, "can_prompt": False}]
    assert result["status"] == "installed" and result["version"] == "0.71.1" and result["verified"]
    assert len(npm_calls) == 2 and len(verify_calls) == 1


def test_existing_npm_package_without_callable_launcher_is_preserved(setup, monkeypatch):
    _, root = setup
    entry = package_fixture(root, binary="dist/index.js")
    npm_calls = []

    def npm(args):
        npm_calls.append(args)
        assert args == ["root", "-g"]
        return subprocess.CompletedProcess(args, 0, str(root), "")

    monkeypatch.setattr(gemini, "run_npm_command", npm)
    monkeypatch.setattr(gemini.subprocess, "run", lambda *a, **k: pytest.fail("missing launcher is not a usable CLI"))
    with pytest.raises(RuntimeError, match="not callable on PATH.*add .* to PATH"):
        gemini.setup_gemini_cli()
    assert entry.is_file() and len(npm_calls) == 1


def test_existing_path_install_is_verified_without_npm_or_replacement(setup, monkeypatch):
    runtime, root = setup
    entry = package_fixture(root)
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(entry))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("valid existing launcher needs no npm"))

    def run(command, **kwargs):
        assert command == [runtime["node_bin"], str(entry), "--version"]
        return subprocess.CompletedProcess(command, 0, "0.60.0\n", "")

    monkeypatch.setattr(gemini.subprocess, "run", run)
    result = gemini.setup_gemini_cli()
    assert result["status"] == "already_installed" and result["version"] == "0.60.0"


def test_official_launcher_from_alternate_npm_prefix_is_preserved(setup, monkeypatch, tmp_path, require_symlink_privilege):
    runtime, _ = setup
    entry = package_fixture(tmp_path / "alternate prefix" / "lib" / "node_modules", binary="dist/index.js")
    launcher = tmp_path / "alternate prefix" / "bin" / "gemini"
    launcher.parent.mkdir()
    launcher.symlink_to(entry)
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(launcher))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("do not replace alternate official installation"))

    def run(command, **kwargs):
        assert command == [runtime["node_bin"], str(entry), "--version"]
        return subprocess.CompletedProcess(command, 0, "0.60.0", "")

    monkeypatch.setattr(gemini.subprocess, "run", run)
    result = gemini.setup_gemini_cli()
    assert result["status"] == "already_installed" and result["binary"] == str(launcher)
    assert launcher.resolve() == entry



def test_windows_existing_cmd_shim_runs_official_js_without_shell(setup, monkeypatch, tmp_path):
    runtime, _ = setup
    prefix = tmp_path / "npm prefix with spaces & punctuation"
    entry = package_fixture(prefix / "node_modules")
    launcher = str(prefix / "gemini.cmd")
    monkeypatch.setattr(gemini.platform, "system", lambda: "Windows")
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: launcher)
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("must keep existing"))

    def run(command, **kwargs):
        assert command == [runtime["node_bin"], str(entry), "--version"]
        assert not kwargs.get("shell") and all("cmd.exe" not in part for part in command)
        return subprocess.CompletedProcess(command, 0, "0.71.1", "")

    monkeypatch.setattr(gemini.subprocess, "run", run)
    result = gemini.setup_gemini_cli()
    assert result["status"] == "already_installed" and result["binary"] == launcher


def test_windows_unknown_existing_launcher_is_preserved(setup, monkeypatch, tmp_path):
    monkeypatch.setattr(gemini.platform, "system", lambda: "Windows")
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(tmp_path / "other" / "gemini.cmd"))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("must not overwrite"))
    with pytest.raises(RuntimeError, match="was not overwritten"):
        gemini.setup_gemini_cli()


@pytest.mark.parametrize("output", ["", "other tool 0.71.1", "not a version"])
def test_invalid_existing_version_does_not_trigger_npm_install(setup, monkeypatch, output):
    _, root = setup
    entry = package_fixture(root)
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(entry))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("must not overwrite"))
    monkeypatch.setattr(gemini.subprocess, "run", lambda command, **k: subprocess.CompletedProcess(command, 0, output, ""))
    with pytest.raises(RuntimeError, match="could not be verified"):
        gemini.setup_gemini_cli()


@pytest.mark.parametrize("failure,expected", [
    (click.Abort(), "Node.js >= 20"), (click.ClickException("Node download failed"), "Node download failed"),
    (OSError("node missing"), "node missing"), (subprocess.TimeoutExpired("node", 60), "timed out"),
])
def test_node_failures_are_reported_without_install_success(setup, monkeypatch, failure, expected):
    def ensure(**kwargs):
        raise failure

    monkeypatch.setattr(gemini, "ensure_nodejs_requirement", ensure)
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a: pytest.fail("no npm after runtime failure"))
    with pytest.raises(RuntimeError, match=expected):
        gemini.setup_gemini_cli()


@pytest.mark.parametrize("stage", ["root", "install", "missing_package", "version"])
def test_npm_and_verification_failures_never_claim_installation(setup, monkeypatch, stage):
    _, root = setup

    def npm(args):
        if args == ["root", "-g"]:
            return subprocess.CompletedProcess(args, 7 if stage == "root" else 0, str(root), "npm root failed" if stage == "root" else "")
        if stage == "version":
            package_fixture(root)
        return subprocess.CompletedProcess(args, 7 if stage == "install" else 0, "", "npm install failed" if stage == "install" else "")

    entry = root / "@google/gemini-cli/bundle/gemini.js"
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(entry) if entry.is_file() else None)
    monkeypatch.setattr(gemini, "run_npm_command", npm)
    monkeypatch.setattr(gemini.subprocess, "run", lambda command, **k: subprocess.CompletedProcess(command, 9, "", "version failed"))
    expected = {"root": "global npm", "install": "npm installation failed", "missing_package": "package was not found", "version": "verification failed"}[stage]
    with pytest.raises(RuntimeError, match=expected):
        gemini.setup_gemini_cli()


@pytest.mark.parametrize("metadata", [
    [], {"name": "other-tool", "bin": {"gemini": "index.js"}},
    {"name": gemini.NPM_PACKAGE, "bin": {"gemini": "../outside.js"}},
    {"name": gemini.NPM_PACKAGE, "bin": {"gemini": "/outside.js"}},
    {"name": gemini.NPM_PACKAGE, "bin": {"gemini": "C:/outside.js"}},
    {"name": gemini.NPM_PACKAGE, "bin": {"gemini": "C:outside.js"}},
    {"name": gemini.NPM_PACKAGE, "bin": {"gemini": "//server/share/bin.js"}},
])
def test_invalid_existing_package_metadata_is_preserved(setup, monkeypatch, metadata):
    _, root = setup
    entry = package_fixture(root)
    package = entry.parents[1]
    text = json.dumps(metadata)
    (package / "package.json").write_text(text)
    monkeypatch.setattr(gemini, "run_npm_command", lambda args: subprocess.CompletedProcess(args, 0, str(root), ""))
    with pytest.raises(RuntimeError, match="Invalid official Gemini"):
        gemini.setup_gemini_cli()
    assert (package / "package.json").read_text() == text


def test_unrelated_executable_with_semver_is_not_accepted_or_executed(setup, monkeypatch, tmp_path):
    launcher = tmp_path / "unrelated" / "gemini"
    launcher.parent.mkdir()
    launcher.write_text("#!/bin/sh\necho 1.2.3\n")
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(launcher))
    monkeypatch.setattr(gemini.subprocess, "run", lambda *a, **k: pytest.fail("unrecognized launcher must not execute"))
    monkeypatch.setattr(gemini, "run_npm_command", lambda *a, **k: pytest.fail("must preserve unrelated executable"))
    with pytest.raises(RuntimeError, match="cannot be identified.*not overwritten"):
        gemini.setup_gemini_cli()
    assert launcher.read_text() == "#!/bin/sh\necho 1.2.3\n"


def test_existing_launcher_must_match_official_package_bin(setup, monkeypatch):
    _, root = setup
    entry = package_fixture(root)
    other = entry.parent / "other.js"
    other.write_text("// unrelated executable in same package directory")
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(other))
    monkeypatch.setattr(gemini.subprocess, "run", lambda *a, **k: pytest.fail("wrong package bin"))
    with pytest.raises(RuntimeError, match="cannot be identified"):
        gemini.setup_gemini_cli()


def test_invalid_launcher_package_metadata_type_is_a_runtime_error(setup, monkeypatch):
    _, root = setup
    entry = package_fixture(root)
    metadata = entry.parents[1] / "package.json"
    metadata.write_text("[]")
    monkeypatch.setattr(gemini.shutil, "which", lambda *a, **k: str(entry))
    with pytest.raises(RuntimeError, match="Invalid Gemini launcher package metadata"):
        gemini.setup_gemini_cli()
    assert metadata.read_text() == "[]"


@pytest.mark.parametrize("system", ["Darwin", "Windows"])
def test_successful_npm_install_without_path_shim_is_not_success(setup, monkeypatch, system):
    _, root = setup
    monkeypatch.setattr(gemini.platform, "system", lambda: system)

    def npm(args):
        if args == ["root", "-g"]:
            return subprocess.CompletedProcess(args, 0, str(root), "")
        package_fixture(root)
        return subprocess.CompletedProcess(args, 0, "installed", "")

    monkeypatch.setattr(gemini, "run_npm_command", npm)
    monkeypatch.setattr(gemini.subprocess, "run", lambda *a, **k: pytest.fail("no usable command"))
    with pytest.raises(RuntimeError, match="not callable on PATH.*Repair a missing launcher"):
        gemini.setup_gemini_cli()
    assert (root / "@google/gemini-cli/package.json").is_file()
