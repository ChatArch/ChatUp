from click.testing import CliRunner

from chatup.cli import main


def test_chatup_setup_help_lists_migrated_commands_without_alias():
    result = CliRunner().invoke(main, ["setup", "--help"])

    assert result.exit_code == 0
    assert "Setup common ChatArch agent tools and workspace helpers." in result.output
    for command in [
        "workspace",
        "nodejs",
        "codex",
        "claude",
        "opencode",
        "hermes",
        "lark-cli",
        "docker",
        "zsh",
    ]:
        assert command in result.output
    assert "\n  alias " not in result.output


def test_chatup_setup_workspace_help_keeps_interactive_flags():
    result = CliRunner().invoke(main, ["setup", "workspace", "--help"])

    assert result.exit_code == 0
    assert "--with-chattool" in result.output
    assert "--with-chatblog" in result.output
    assert "--with-memory" in result.output
    assert "-i, --interactive" in result.output
    assert "-I, --no-interactive" in result.output


def test_all_migrated_setup_commands_expose_help():
    commands = [
        "cc-connect",
        "chrome",
        "claude",
        "codex",
        "docker",
        "frp",
        "hermes",
        "lark-cli",
        "nodejs",
        "opencode",
        "workspace",
        "zsh",
    ]

    for command in commands:
        result = CliRunner().invoke(main, ["setup", command, "--help"])
        assert result.exit_code == 0, command
        assert "--help" in result.output


def test_setup_alias_command_is_not_registered():
    result = CliRunner().invoke(main, ["setup", "alias", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_opencode_setup_no_longer_exposes_legacy_chatloop_preset():
    result = CliRunner().invoke(main, ["setup", "opencode", "--help"])

    assert result.exit_code == 0
    assert "auto-loop" in result.output
    assert "chatloop" not in result.output.lower()


def test_cc_connect_setup_installs_chatarch_package(monkeypatch):
    import chatup.setup.cc_connect as cc_connect

    commands = []
    monkeypatch.setattr(cc_connect, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        cc_connect,
        "should_install_global_npm_package",
        lambda package_name, display_name, **kwargs: (
            package_name == "@chatarch/cc-connect" and display_name == "cc-connect"
        ),
    )

    class Result:
        returncode = 0
        stderr = ""

    def fake_run_npm_command(args):
        commands.append(args)
        return Result()

    monkeypatch.setattr(cc_connect, "run_npm_command", fake_run_npm_command)

    result = CliRunner().invoke(main, ["setup", "cc-connect", "-I"])

    assert result.exit_code == 0, result.output
    assert commands == [["install", "-g", "@chatarch/cc-connect"]]
