from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import click
from click.testing import CliRunner

from chatup.cli import main
from chatup.utils import platforming


def test_ci_has_bounded_windows_node_codex_smoke():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "windows-node-codex-smoke:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "timeout-minutes: 18" in workflow
    assert "CHATARCH_HOME" in workflow
    assert "CODEX_HOME" in workflow
    assert "chatup nodejs -I" in workflow
    assert "ci-placeholder-not-a-secret" in workflow
    assert "Get-Command node -All" in workflow
    assert "nodeCandidateDirs" in workflow
    assert "[IO.Path]::DirectorySeparatorChar" in workflow
    assert 'Join-Path $env:CHATARCH_HOME "nodejs/npm/codex.cmd"' in workflow
    assert "import tomllib" in workflow
    assert 'config["forced_login_method"] == "api"' in workflow
    assert 'assert "preferred_auth_method" not in config' in workflow


def test_windows_native_smoke_aborts_on_every_nonzero_native_command():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    native_job = workflow.split("windows-node-codex-smoke:", 1)[1]
    assert "$PSNativeCommandUseErrorActionPreference = $true" in native_job


def test_ci_smokes_windows_managed_opencode_launcher_and_config():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text()
    job = workflow.split("windows-node-codex-smoke:", 1)[1]
    assert "chatup opencode --api-key" in job
    assert 'Join-Path $env:CHATARCH_HOME "nodejs/npm/opencode.cmd"' in job
    assert 'config["model"] == "opencode/gpt-5.6-terra"' in job


def test_uv_windows_installer_uses_powershell(monkeypatch):
    import chatup.setup.uv as uv_setup

    commands = []

    def fake_run_command(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(uv_setup, "_run_command", fake_run_command)
    monkeypatch.setattr(uv_setup, "find_uv", lambda: r"C:\Users\me\.local\bin\uv.exe")

    assert uv_setup.install_uv_with_official_script().endswith("uv.exe")
    assert commands == [
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://astral.sh/uv/install.ps1 | iex",
        ]
    ]
    assert platforming.venv_python_path(Path("C:/chatarch/venv")).parts[-2:] == (
        "Scripts",
        "python.exe",
    )
    assert platforming.venv_activate_hint(Path("C:/chatarch/venv")).endswith(
        str(Path("Scripts") / "Activate.ps1")
    )


def test_cursor_agent_windows_installer_uses_official_powershell_and_rediscovers_localappdata(monkeypatch, tmp_path):
    import chatup.setup.cursor_agent as cursor_setup

    local_app_data = tmp_path / "Local App Data"
    installed = local_app_data / "cursor-agent" / "cursor-agent.cmd"
    commands = []

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(cursor_setup, "is_windows", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(cursor_setup.shutil, "which", lambda _: None)

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text("@echo off\r\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(cursor_setup.subprocess, "run", fake_run)

    assert cursor_setup._install_cursor_agent_if_needed() is True
    assert cursor_setup._resolve_cursor_agent_binary() == str(installed)
    assert commands == [
        ([
            "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-Command", "irm 'https://cursor.com/install?win32=true' | iex",
        ], {"text": True, "capture_output": True, "timeout": 300}),
    ]


def test_hermes_windows_installer_reads_resolved_paths_before_noninteractive_install(monkeypatch, tmp_path):
    from chatup.setup import hermes as hermes_setup

    installer = tmp_path / "installer.ps1"
    installer.write_text("# inert fixture", encoding="utf-8")
    home = tmp_path / "ChatArch Home"
    commands = []
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(hermes_setup, "is_windows", lambda: True)

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 0,
            json.dumps({"hermes_home": str(home), "install_dir": str(home / "hermes-agent")}),
            "",
        )

    monkeypatch.setattr(hermes_setup.subprocess, "run", fake_run)
    hermes_setup._run_installer(installer, home)

    base = [
        "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(installer),
        "-NonInteractive", "-HermesHome", str(home), "-InstallDir", str(home / "hermes-agent"),
    ]
    assert commands == [
        (base + ["-ShowResolvedPaths"], {"env": {**os.environ, "HERMES_HOME": str(home)}, "text": True, "capture_output": True}),
        (base, {"env": {**os.environ, "HERMES_HOME": str(home)}, "text": True}),
    ]


def test_hermes_windows_downloads_fork_installer_when_no_cached_or_packaged_asset(monkeypatch, tmp_path):
    from chatup.setup import hermes as hermes_setup

    downloaded = tmp_path / "chatarch" / "cache" / "chatup" / "hermes" / "install.ps1"
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(hermes_setup, "is_windows", lambda: True)
    monkeypatch.setattr(hermes_setup, "_cache_installer_path", lambda: downloaded)
    monkeypatch.setattr(hermes_setup, "_packaged_installer_path", lambda: tmp_path / "missing.ps1")
    calls = []

    def fake_download():
        calls.append(True)
        downloaded.parent.mkdir(parents=True)
        downloaded.write_text("# fixture", encoding="utf-8")
        return downloaded

    monkeypatch.setattr(hermes_setup, "_download_installer", fake_download)
    assert hermes_setup._resolve_installer(None, False) == downloaded
    assert calls == [True]


def test_frp_windows_arch_aliases_use_official_asset_names(monkeypatch):
    import chatup.setup.frp as frp_setup

    monkeypatch.setattr(frp_setup.platform, "machine", lambda: "AMD64")
    assert frp_setup.get_system_arch() == "amd64"
    monkeypatch.setattr(frp_setup.platform, "machine", lambda: "ARM64")
    assert frp_setup.get_system_arch() == "arm64"




def test_nodejs_windows_reuses_path_runtime(monkeypatch):
    import chatup.setup.nodejs as nodejs_setup

    runtime = nodejs_setup._build_runtime(
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files\nodejs\npm.cmd",
        "v22.11.0",
        "10.9.0",
        "path",
        npm_cli=r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js",
    )
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "_detect_nodejs_runtime", lambda: runtime)

    result = CliRunner().invoke(main, ["nodejs"])

    assert result.exit_code == 0, result.output
    assert "ChatUp reuses node/npm from PATH on Windows" in result.output


def test_nodejs_windows_requires_npm_cli_for_a_usable_runtime(monkeypatch):
    import chatup.setup.nodejs as nodejs_setup

    runtime = nodejs_setup._build_runtime(
        r"C:\\Program Files\\nodejs\\node.exe",
        r"C:\\Program Files\\nodejs\\npm.cmd",
        "v22.11.0",
        "10.9.0",
        "path",
    )
    monkeypatch.setattr(platforming, "WINDOWS", True)

    assert not nodejs_setup.has_required_nodejs(runtime=runtime)


def test_nodejs_help_describes_windows_portable_bootstrap():
    result = CliRunner().invoke(main, ["nodejs", "--help"])

    assert result.exit_code == 0, result.output
    assert "ChatArch portable ZIP on Windows" in result.output


def test_nodejs_windows_bootstraps_chatarch_runtime_when_path_is_missing(monkeypatch):
    import chatup.setup.nodejs as nodejs_setup

    missing = nodejs_setup._build_runtime("", "", "", "", "path")
    managed = {
        **nodejs_setup._build_runtime(
            r"C:\\ChatArch\\nodejs\\node.exe",
            r"C:\\ChatArch\\nodejs\\npm.cmd",
            "v22.14.0",
            "10.9.2",
            "chatarch",
        ),
        "npm_cli": r"C:\\ChatArch\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
    }
    calls = []

    def bootstrap(*, min_major):
        calls.append(min_major)
        return managed

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "_detect_nodejs_runtime", lambda: missing)
    monkeypatch.setattr(
        nodejs_setup,
        "_bootstrap_windows_node_lts",
        bootstrap,
        raising=False,
    )
    monkeypatch.setattr(nodejs_setup, "ensure_windows_user_path", lambda runtime: None)

    result = CliRunner().invoke(main, ["nodejs", "-I"])

    assert result.exit_code == 0, result.output
    assert calls == [nodejs_setup.MIN_NODEJS_MAJOR]
    assert "ChatArch-managed Node.js ready: v22.14.0" in result.output


def test_windows_node_requirement_bootstraps_for_npm_consumers(monkeypatch):
    import chatup.setup.nodejs as nodejs_setup

    missing = nodejs_setup._build_runtime("", "", "", "", "path")
    managed = {
        **nodejs_setup._build_runtime(
            r"C:\\ChatArch\\nodejs\\node.exe",
            r"C:\\ChatArch\\nodejs\\npm.cmd",
            "v22.14.0",
            "10.9.2",
            "chatarch",
        ),
        "npm_cli": r"C:\\ChatArch\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
    }
    calls = []

    def bootstrap(*, min_major):
        calls.append(min_major)
        return managed

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "_detect_nodejs_runtime", lambda: missing)
    monkeypatch.setattr(nodejs_setup, "_bootstrap_windows_node_lts", bootstrap)

    runtime = None
    try:
        runtime = nodejs_setup.ensure_nodejs_requirement(
            interactive=False,
            can_prompt=False,
        )
    except click.Abort:
        pass

    assert runtime == managed
    assert calls == [nodejs_setup.MIN_NODEJS_MAJOR]


def test_nodejs_windows_extracts_verified_zip_under_chatarch_home(monkeypatch, tmp_path):
    import chatup.setup.nodejs as nodejs_setup

    archive_name = "node-v22.14.0-win-x64.zip"
    archive = tmp_path / archive_name
    archive_root = archive_name.removesuffix(".zip")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(f"{archive_root}/node.exe", b"node")
        bundle.writestr(
            f"{archive_root}/node_modules/npm/bin/npm-cli.js", b"npm cli"
        )
    release = {
        "version": "v22.14.0",
        "archive_name": archive_name,
        "archive_url": f"https://nodejs.org/dist/v22.14.0/{archive_name}",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    downloads = []
    chatarch_home = tmp_path / "ChatArch 空格 &!"

    def download(url, destination):
        downloads.append(url)
        shutil.copyfile(archive, destination)

    def command_output(command):
        if str(command[-1]) == "-v":
            return "v22.14.0"
        if str(command[-1]) == "--version":
            return "10.9.2"
        return ""

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "CHATARCH_HOME", chatarch_home, raising=False)
    monkeypatch.setattr(nodejs_setup.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        nodejs_setup,
        "_resolve_windows_node_release",
        lambda **_kwargs: release,
        raising=False,
    )
    monkeypatch.setattr(
        nodejs_setup, "_download_file", download, raising=False
    )
    monkeypatch.setattr(nodejs_setup, "_get_cmd_output", command_output)
    monkeypatch.setattr(nodejs_setup, "ensure_windows_user_path", lambda runtime: None)

    first = CliRunner().invoke(main, ["nodejs", "-I"])
    second = CliRunner().invoke(main, ["nodejs", "-I"])

    runtime_root = chatarch_home / "nodejs" / "runtimes" / archive_root
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert downloads == [release["archive_url"]]
    assert (runtime_root / "node.exe").is_file()
    assert (runtime_root / "node_modules" / "npm" / "bin" / "npm-cli.js").is_file()
    assert "ChatArch-managed Node.js ready: v22.14.0" in first.output
    assert "ChatUp reuses ChatArch-managed node/npm on Windows" in second.output


def test_nodejs_windows_rejects_zip_path_escape(monkeypatch, tmp_path):
    import chatup.setup.nodejs as nodejs_setup

    archive_name = "node-v22.14.0-win-x64.zip"
    archive = tmp_path / archive_name
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", b"escape")
    release = {
        "version": "v22.14.0",
        "archive_name": archive_name,
        "archive_url": f"https://nodejs.org/dist/v22.14.0/{archive_name}",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    chatarch_home = tmp_path / "chatarch"

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "CHATARCH_HOME", chatarch_home, raising=False)
    monkeypatch.setattr(nodejs_setup.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        nodejs_setup,
        "_resolve_windows_node_release",
        lambda **_kwargs: release,
        raising=False,
    )
    monkeypatch.setattr(
        nodejs_setup,
        "_download_file",
        lambda _url, destination: shutil.copyfile(archive, destination),
        raising=False,
    )

    result = CliRunner().invoke(main, ["nodejs", "-I"])

    assert result.exit_code != 0
    assert "unsafe archive path" in result.output
    assert not (tmp_path / "outside.txt").exists()


def test_nodejs_windows_rejects_bad_official_sha256(monkeypatch, tmp_path):
    import chatup.setup.nodejs as nodejs_setup

    archive_name = "node-v22.14.0-win-x64.zip"
    archive = tmp_path / archive_name
    archive_root = archive_name.removesuffix(".zip")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(f"{archive_root}/node.exe", b"node")
        bundle.writestr(
            f"{archive_root}/node_modules/npm/bin/npm-cli.js", b"npm cli"
        )
    release = {
        "version": "v22.14.0",
        "archive_name": archive_name,
        "archive_url": f"https://nodejs.org/dist/v22.14.0/{archive_name}",
        "sha256": "0" * 64,
    }
    chatarch_home = tmp_path / "chatarch"

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "CHATARCH_HOME", chatarch_home, raising=False)
    monkeypatch.setattr(nodejs_setup.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        nodejs_setup,
        "_resolve_windows_node_release",
        lambda **_kwargs: release,
        raising=False,
    )
    monkeypatch.setattr(
        nodejs_setup,
        "_download_file",
        lambda _url, destination: shutil.copyfile(archive, destination),
        raising=False,
    )

    result = CliRunner().invoke(main, ["nodejs", "-I"])

    assert result.exit_code != 0
    assert "SHA-256 mismatch" in result.output
    assert not (chatarch_home / "nodejs" / "runtimes" / archive_root).exists()


def test_windows_setup_persists_managed_node_and_npm_paths_for_current_user(
    monkeypatch, tmp_path
):
    import types
    import chatup.setup.nodejs as nodejs_setup

    runtime_dir = tmp_path / "node runtime"
    runtime = nodejs_setup._build_runtime(
        str(runtime_dir / "node.exe"), str(runtime_dir / "npm.cmd"), "v22.14.0", "10.9.2", "chatarch",
        npm_cli=str(runtime_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"),
    )
    values = {"Path": r"C:\\Users\\me\\bin;C:\\Other"}
    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER=object(), KEY_READ=1, KEY_WRITE=2, REG_EXPAND_SZ=2,
        OpenKey=lambda *args: object(),
        QueryValueEx=lambda key, name: (values[name], 2),
        SetValueEx=lambda key, name, reserved, value_type, value: values.__setitem__(name, value),
        CloseKey=lambda key: None,
    )
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setitem(__import__("sys").modules, "winreg", fake_winreg)
    monkeypatch.setattr(nodejs_setup, "_windows_node_home", lambda: tmp_path)
    monkeypatch.setenv("PATH", r"C:\\Users\\me\\bin;C:\\Other")

    nodejs_setup.ensure_windows_user_path(runtime)
    nodejs_setup.ensure_windows_user_path(runtime)

    expected = [str(runtime_dir), str(tmp_path / "npm")]
    assert values["Path"].split(";")[:2] == expected
    assert values["Path"].split(";").count(str(runtime_dir)) == 1
    assert values["Path"].split(";").count(str(tmp_path / "npm")) == 1
    assert __import__("os").environ["PATH"].split(";")[:2] == expected


def test_lark_cli_uses_managed_windows_launcher_after_npm_install(monkeypatch, tmp_path):
    import chatup.setup.lark_cli as lark_cli

    prefix = tmp_path / "nodejs" / "npm"
    launcher = prefix / "lark-cli.cmd"
    runtime = {"source": "chatarch", "node_bin": str(tmp_path / "node.exe")}
    calls = []
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(lark_cli, "_detect_nodejs_runtime", lambda: runtime)
    monkeypatch.setattr(lark_cli, "managed_npm_launcher", lambda current, name: launcher)
    monkeypatch.setattr(lark_cli.subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)) or subprocess.CompletedProcess(command, 0, "", ""))

    result = lark_cli._run_lark_cli_command(["config", "init"])

    assert result.returncode == 0
    assert calls[0][0] == [str(launcher), "config", "init"]
    assert calls[0][1].get("shell") is None


def test_claude_honors_native_config_home_and_preserves_unrelated_values(monkeypatch, tmp_path):
    import chatup.setup.claude as claude

    claude_home = tmp_path / "native-claude"
    claude_home.mkdir()
    (claude_home / "settings.json").write_text('{"theme":"dark","env":{"KEEP":"yes"}}')
    (claude_home / "config.json").write_text('{"other":"keep","primaryApiKey":"old"}')
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
    import chatup.setup.nodejs as nodejs
    monkeypatch.setattr(nodejs, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(nodejs, "should_install_global_npm_package", lambda *args, **kwargs: False)

    claude.setup_claude(auth_token="fixture-token", interactive=False)

    settings = json.loads((claude_home / "settings.json").read_text())
    config = json.loads((claude_home / "config.json").read_text())
    assert settings["theme"] == "dark"
    assert settings["env"]["KEEP"] == "yes"
    assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "fixture-token"
    assert config["other"] == "keep"


def test_remotion_uses_shared_windows_node_npm_cli(monkeypatch, tmp_path):
    import chatup.setup.remotion as remotion

    node = tmp_path / "node.exe"
    npm_cli = tmp_path / "node_modules" / "npm" / "bin" / "npm-cli.js"
    runtime = {"node_bin": str(node), "npm_bin": str(tmp_path / "npm.cmd"), "npm_cli": str(npm_cli), "source": "chatarch"}
    calls = []
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(remotion, "_detect_nodejs_runtime", lambda: runtime)
    monkeypatch.setattr(remotion, "has_required_nodejs", lambda **kwargs: True)
    monkeypatch.setattr(remotion, "_run", lambda command, **kwargs: calls.append((command, kwargs)) or ("v24.0.0" if command[0] == str(node) else "11.0.0"))

    remotion._runtime()

    assert calls[1][0] == [str(node), str(npm_cli), "--version"]
    assert calls[1][1].get("shell") is None




def test_windows_npm_uses_detected_node_and_npm_cli_as_argument_list(monkeypatch, tmp_path):
    import chatup.setup.nodejs as nodejs_setup

    runtime_dir = tmp_path / "Node 空格 &!"
    runtime_dir.mkdir()
    node_bin = runtime_dir / "node.exe"
    npm_cmd = runtime_dir / "npm.cmd"
    npm_cli = runtime_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
    npm_cli.parent.mkdir(parents=True)
    node_bin.write_text("node", encoding="utf-8")
    npm_cmd.write_text("npm", encoding="utf-8")
    npm_cli.write_text("npm cli", encoding="utf-8")
    cwd = tmp_path / "工作目录 &;!"
    cwd.mkdir()
    runtime = {
        **nodejs_setup._build_runtime(
            str(node_bin), str(npm_cmd), "v22.14.0", "10.9.2", "path"
        ),
        "npm_cli": str(npm_cli),
    }
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "_detect_nodejs_runtime", lambda: runtime)
    monkeypatch.setattr(nodejs_setup.subprocess, "run", fake_run)

    result = nodejs_setup.run_npm_command(
        ["install", "-g", "package;$(not-a-shell-command)", "value&more"],
        cwd=cwd,
    )

    assert result.returncode == 0
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == [
        str(node_bin),
        str(npm_cli),
        "install",
        "-g",
        "package;$(not-a-shell-command)",
        "value&more",
    ]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["cwd"] == cwd
    assert kwargs.get("shell") is None
    assert kwargs["env"]["PATH"].split(os.pathsep)[0] == str(runtime_dir)


def test_windows_managed_node_runtime_keeps_global_npm_prefix_under_chatarch(
    monkeypatch, tmp_path
):
    import chatup.setup.nodejs as nodejs_setup

    chatarch_home = tmp_path / "ChatArch 空格 &!"
    runtime_dir = chatarch_home / "nodejs" / "runtimes" / "node-v22.14.0-win-x64"
    runtime_dir.mkdir(parents=True)
    node_bin = runtime_dir / "node.exe"
    npm_cli = runtime_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
    npm_cli.parent.mkdir(parents=True)
    node_bin.write_text("node", encoding="utf-8")
    npm_cli.write_text("npm cli", encoding="utf-8")
    runtime = nodejs_setup._build_runtime(
        str(node_bin),
        str(runtime_dir / "npm.cmd"),
        "v22.14.0",
        "10.9.2",
        "chatarch",
        npm_cli=str(npm_cli),
    )

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(nodejs_setup, "CHATARCH_HOME", chatarch_home)

    env = nodejs_setup.node_runtime_env(runtime, {"PATH": str(tmp_path / "other")})
    npm_prefix = chatarch_home / "nodejs" / "npm"

    assert env["NPM_CONFIG_PREFIX"] == str(npm_prefix)
    assert env["PATH"].split(os.pathsep)[:2] == [str(runtime_dir), str(npm_prefix)]


def test_playwright_windows_uses_shared_node_npm_invocation(monkeypatch, tmp_path):
    from chatup.runtime import playwright

    runtime_dir = tmp_path / "Node 空格 &!"
    runtime_dir.mkdir()
    node_bin = runtime_dir / "node.exe"
    npm_cmd = runtime_dir / "npm.cmd"
    npm_cli = runtime_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
    npm_cli.parent.mkdir(parents=True)
    node_bin.write_text("node", encoding="utf-8")
    npm_cmd.write_text("npm", encoding="utf-8")
    npm_cli.write_text("npm cli", encoding="utf-8")
    runtime = {
        "node_bin": str(node_bin),
        "npm_bin": str(npm_cmd),
        "npm_cli": str(npm_cli),
        "node_version": "v22.14.0",
        "npm_version": "10.9.2",
        "node_major": 22,
        "source": "chatarch",
    }
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    binary = staging_dir / "browsers" / "chromium-1228" / "chrome.exe"
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        if len(calls) == 1:
            package_dir = staging_dir / "package" / "node_modules"
            (package_dir / "playwright").mkdir(parents=True)
            (package_dir / "playwright-core").mkdir(parents=True)
            (package_dir / "playwright" / "package.json").write_text(
                json.dumps({"version": "1.61.1"}), encoding="utf-8"
            )
            (package_dir / "playwright" / "cli.js").write_text(
                "cli", encoding="utf-8"
            )
            (package_dir / "playwright-core" / "browsers.json").write_text(
                json.dumps(
                    {
                        "browsers": [
                            {
                                "name": "chromium",
                                "revision": "1228",
                                "browserVersion": "149.0.7827.55",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, "", "")
        if len(calls) == 2:
            binary.parent.mkdir(parents=True)
            binary.write_text("browser", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 0, str(binary), "")

    monkeypatch.setattr(platforming, "WINDOWS", True)
    payload = playwright._install_with_npm(
        "1.61.1",
        "chromium",
        staging_dir,
        runtime=runtime,
        runner=runner,
    )

    assert payload.binary_path == binary
    assert calls[0][0][:3] == [str(node_bin), str(npm_cli), "install"]
    assert calls[0][1]["env"]["PATH"].split(os.pathsep)[0] == str(runtime_dir)
    assert calls[0][1].get("shell") is None


def test_docker_windows_prints_desktop_guidance(monkeypatch):
    import chatup.setup.docker as docker_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(docker_setup, "_docker_version", lambda: None)
    monkeypatch.setattr(docker_setup, "_docker_compose_version", lambda: None)

    result = CliRunner().invoke(main, ["docker", "-I"])

    assert result.exit_code == 0, result.output
    assert "Install Docker Desktop for Windows" in result.output
    assert "Docker group/systemd checks are skipped on Windows" in result.output


def test_mysql_windows_uses_zip_and_tcp_config(monkeypatch, tmp_path):
    import chatup.setup.mysql as mysql_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(mysql_setup.platform, "system", lambda: "Windows")
    monkeypatch.setattr(mysql_setup.platform, "machine", lambda: "AMD64")

    assert mysql_setup.detect_mysql_platform() == "winx64"
    url, checksum = mysql_setup.mysql_asset_urls("8.4.6")
    assert url.endswith("mysql-8.4.6-winx64.zip")
    assert checksum.endswith("mysql-8.4.6-winx64.zip.md5")

    layout = mysql_setup.mysql_layout(home=tmp_path)
    config = mysql_setup.render_my_cnf(layout, tmp_path / "runtime")
    assert "socket=" not in config
    assert "host=127.0.0.1" in config
    assert mysql_setup.client_command(home=tmp_path)[:2] == [
        str(tmp_path / "runtimes" / "mysql" / "8.4.6" / "bin" / "mysql.exe"),
        "-uroot",
    ]


def test_gitea_windows_service_fails_before_systemctl(monkeypatch, tmp_path):
    import chatup.setup.gitea as gitea_setup

    target = tmp_path / "gitea.exe"
    target.write_text("binary", encoding="utf-8")
    monkeypatch.setattr(platforming, "WINDOWS", True)
    monkeypatch.setattr(
        gitea_setup,
        "install_gitea_release_binary",
        lambda **kwargs: (target, "1.0.0"),
    )
    monkeypatch.setattr(
        gitea_setup,
        "verify_gitea_binary",
        lambda path, version: f"gitea version {version}",
    )

    result = CliRunner().invoke(main, ["gitea", "--service", "-I"])

    assert result.exit_code != 0
    assert "systemd services" in result.output


def test_frp_windows_zip_extracts_exe(monkeypatch, tmp_path):
    import chatup.setup.frp as frp_setup

    monkeypatch.setattr(platforming, "WINDOWS", True)
    archive = tmp_path / "frp.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("frp_0.66.0_windows_amd64/frpc.exe", b"binary")

    extracted = Path(frp_setup.extract_frp(archive, tmp_path / "out", "frpc.exe"))

    assert extracted == tmp_path / "out" / "frpc.exe"
    assert extracted.read_bytes() == b"binary"
