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
