from __future__ import annotations

from click.testing import CliRunner

from chatup.cli import main


def test_twikoo_layout_uses_chatarch_home_and_instance_scoped_paths(tmp_path):
    from chatup.setup.twikoo import twikoo_layout

    layout = twikoo_layout(name="chatblog", version="1.7.15", home=tmp_path / "twikoo")

    assert layout.home == tmp_path / "twikoo"
    assert layout.runtime == tmp_path / "twikoo" / "runtimes" / "1.7.15"
    assert layout.binary == tmp_path / "twikoo" / "runtimes" / "1.7.15" / "twikoo"
    assert layout.instance == tmp_path / "twikoo" / "instances" / "chatblog"
    assert layout.env == tmp_path / "twikoo" / "instances" / "chatblog" / "env" / "twikoo.env"
    assert layout.data == tmp_path / "twikoo" / "instances" / "chatblog" / "data"
    assert layout.logs == tmp_path / "twikoo" / "instances" / "chatblog" / "logs"
    assert layout.service.name == "chatup-twikoo-chatblog.service"


def test_twikoo_render_env_and_service_are_instance_scoped(tmp_path):
    from chatup.setup.twikoo import render_env, render_service, service_name, twikoo_layout

    layout = twikoo_layout(name="chatblog", version="1.7.15", home=tmp_path / "twikoo")

    env_text = render_env(layout, port=8892, bind_address="127.0.0.1")
    assert "TWIKOO_HOST=127.0.0.1" in env_text
    assert "TWIKOO_PORT=8892" in env_text
    assert f"TWIKOO_DATA={layout.data}" in env_text
    assert "MONGODB" not in env_text

    service_text = render_service(layout, name="chatblog")
    assert service_name("chatblog") == "chatup-twikoo-chatblog.service"
    assert f"WorkingDirectory={layout.instance}" in service_text
    assert f"EnvironmentFile={layout.env}" in service_text
    assert f"ExecStart={layout.binary}" in service_text
    assert "WantedBy=default.target" in service_text


def test_twikoo_help_exposes_multi_instance_binary_installer_options():
    result = CliRunner().invoke(main, ["twikoo", "--help"])

    assert result.exit_code == 0, result.output
    assert "--version" in result.output
    assert "1.7.15" in result.output
    assert "--repo" in result.output
    assert "twikoojs/twikoo" in result.output
    assert "--home" in result.output
    assert "--name" in result.output
    assert "--port" in result.output
    assert "--bind-address" in result.output
    assert "--start / --no-start" in result.output
    assert "--smoke / --no-smoke" in result.output


def test_twikoo_cli_prepares_named_instance_without_starting(monkeypatch, tmp_path):
    import chatup.setup.twikoo as twikoo_setup

    calls = []
    monkeypatch.setattr(
        twikoo_setup,
        "export_layout",
        lambda **kwargs: {
            "instance": str(tmp_path / "twikoo" / "instances" / kwargs["name"]),
            "service": str(tmp_path / f"chatup-twikoo-{kwargs['name']}.service"),
        },
    )
    monkeypatch.setattr(
        twikoo_setup,
        "install_twikoo_binary",
        lambda **kwargs: calls.append(("install", kwargs))
        or {"binary": str(tmp_path / "twikoo" / "runtimes" / kwargs["version"] / "twikoo"), "reused": False},
    )
    monkeypatch.setattr(
        twikoo_setup,
        "init_instance",
        lambda **kwargs: calls.append(("init", kwargs))
        or {"env": str(tmp_path / "twikoo" / "instances" / kwargs["name"] / "env" / "twikoo.env")},
    )
    monkeypatch.setattr(
        twikoo_setup,
        "install_service",
        lambda **kwargs: calls.append(("service", kwargs))
        or {"unit": f"chatup-twikoo-{kwargs['name']}.service"},
    )

    result = CliRunner().invoke(
        main,
        [
            "twikoo",
            "--home",
            str(tmp_path / "twikoo"),
            "--name",
            "chatblog",
            "--port",
            "8892",
            "--no-start",
            "--no-smoke",
        ],
    )

    assert result.exit_code == 0, result.output
    assert [name for name, _ in calls] == ["install", "init", "service"]
    assert calls[0][1]["repo"] == "twikoojs/twikoo"
    assert calls[1][1]["name"] == "chatblog"
    assert calls[1][1]["port"] == 8892
    assert calls[1][1]["bind_address"] == "127.0.0.1"
    assert "chatup-twikoo-chatblog.service" in result.output


def test_twikoo_smoke_requires_start():
    result = CliRunner().invoke(main, ["twikoo", "--no-install", "--no-init", "--no-service", "--smoke"])

    assert result.exit_code != 0
    assert "--smoke requires --start" in result.output
