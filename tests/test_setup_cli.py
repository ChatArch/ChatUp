from click.testing import CliRunner

from chatup.cli import main


def test_chatup_setup_help_lists_migrated_commands():
    result = CliRunner().invoke(main, ["setup", "--help"])

    assert result.exit_code == 0
    assert "Setup common ChatArch agent tools and workspace helpers." in result.output
    for command in [
        "workspace",
        "alias",
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
        "alias",
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


def test_opencode_setup_no_longer_exposes_legacy_chatloop_preset():
    result = CliRunner().invoke(main, ["setup", "opencode", "--help"])

    assert result.exit_code == 0
    assert "auto-loop" in result.output
    assert "chatloop" not in result.output.lower()
