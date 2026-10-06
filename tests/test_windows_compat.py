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
    assert "timeout-minutes: 12" in workflow
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
