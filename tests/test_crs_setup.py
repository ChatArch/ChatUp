import os
import subprocess

from click.testing import CliRunner

from chatup.cli import main


def test_chatup_crs_help_exposes_local_install_options():
    result = CliRunner().invoke(main, ["crs", "--help"])

    assert result.exit_code == 0, result.output
    assert "--package" in result.output
    assert "@chatarch/claude-relay-service@1.0.0" in result.output
    assert "--install-dir" in result.output
    assert "--redis-port" in result.output
    assert "--port" in result.output
    assert "--start / --no-start" in result.output
    assert "--smoke / --no-smoke" in result.output


def test_chatup_crs_invokes_install_flow(monkeypatch, tmp_path):
    import chatup.setup.crs as crs

    calls = []

    def fake_install(**kwargs):
        calls.append(kwargs)
        return {
            "status": "installed",
            "crs_url": "http://127.0.0.1:12402",
            "install_dir": str(kwargs["install_dir"]),
        }

    monkeypatch.setattr(crs, "setup_crs", fake_install)

    result = CliRunner().invoke(
        main,
        [
            "crs",
            "--install-dir",
            str(tmp_path / "crs"),
            "--redis-port",
            "6382",
            "--port",
            "12402",
            "--no-start",
            "--no-smoke",
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "package": "@chatarch/claude-relay-service@1.0.0",
            "install_dir": tmp_path / "crs",
            "redis_port": 6382,
            "port": 12402,
            "start": False,
            "smoke": False,
            "interactive": False,
            "log_level": "INFO",
        }
    ]
    assert "http://127.0.0.1:12402" in result.output


def test_chatup_crs_rejects_smoke_without_start():
    result = CliRunner().invoke(main, ["crs", "--no-start", "-I"])

    assert result.exit_code != 0
    assert "--smoke requires --start" in result.output
    assert "--no-smoke" in result.output


def test_setup_crs_uses_detected_npm_runtime(monkeypatch, tmp_path):
    import chatup.setup.crs as crs

    install_dir = tmp_path / "crs"
    npm_bin = tmp_path / "node" / "bin" / "npm"
    npm_bin.parent.mkdir(parents=True)
    npm_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    package_root = install_dir / "app" / "node_modules" / "@chatarch" / "claude-relay-service"
    config_dir = package_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.example.js").write_text("module.exports = {};\n", encoding="utf-8")

    ensure_calls = []
    command_calls = []
    setup_calls = []

    def fake_ensure_nodejs_requirement(**kwargs):
        ensure_calls.append(kwargs)
        return {"npm_bin": str(npm_bin)}

    def fake_run_command(args, **kwargs):
        command_calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    def fake_subprocess_run(args, **kwargs):
        setup_calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(crs, "ensure_nodejs_requirement", fake_ensure_nodejs_requirement)
    monkeypatch.setattr(crs, "start_local_redis", lambda *_args, **_kwargs: {"conf": "redis.conf"})
    monkeypatch.setattr(crs, "run_command", fake_run_command)
    monkeypatch.setattr(crs.subprocess, "run", fake_subprocess_run)

    result = crs.setup_crs(
        install_dir=install_dir,
        redis_port=6383,
        port=12403,
        start=False,
        smoke=False,
        interactive=False,
    )

    assert result["status"] == "installed"
    assert ensure_calls == [{"interactive": False, "can_prompt": False, "log_level": "INFO"}]
    assert command_calls
    assert all(call[0][0] == str(npm_bin) for call in command_calls)
    assert setup_calls[0][0][0] == str(npm_bin)
    assert setup_calls[0][1]["env"]["PATH"].split(os.pathsep)[0] == str(npm_bin.parent.resolve())
    assert setup_calls[0][1]["env"]["ADMIN_USERNAME"] == "crs_local_admin"
