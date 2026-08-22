from click.testing import CliRunner

from chatup import __version__
from chatup.cli import main


def test_version_present():
    assert __version__ == "0.2.13"


def test_cli_help():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert main.name == "chatup"
    assert "ChatUp CLI" in result.output
    assert "doctor" in result.output
    assert "--tree" in result.output
    assert "--tree-brief" in result.output


def test_cli_tree_lists_registered_command_surface_with_signatures():
    result = CliRunner().invoke(main, ["--tree"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "chatup"
    assert lines.count("chatup") == 1
    assert all("  # " in line for line in lines[1:])
    assert "--version" in result.output
    assert "--tree" in result.output
    assert "--tree-brief" in result.output
    for command in main.commands:
        assert command in result.output
    for leaf in ("install", "list", "show", "path", "doctor", "remove", "gc"):
        assert leaf in result.output
    assert "[--match-browser MATCH-BROWSER]" in result.output
    assert "[--minimum-age-hours MINIMUM-AGE-HOURS]" in result.output
    assert "Remove one exact managed installation." in result.output
    assert "Install/configure Cursor Agent CLI auth and config files." in result.output


def test_cli_tree_brief_keeps_registered_nodes_and_omits_signatures():
    result = CliRunner().invoke(main, ["--tree-brief"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "chatup"
    assert lines.count("chatup") == 1
    assert all("  # " in line for line in lines[1:])
    for command in main.commands:
        assert command in result.output
    for expected in ("--version", "--tree", "--tree-brief", "install", "remove", "gc"):
        assert expected in result.output
    assert "[--match-browser MATCH-BROWSER]" not in result.output
    assert "[--minimum-age-hours MINIMUM-AGE-HOURS]" not in result.output
    assert "[VERSION]" not in result.output


def test_cli_doctor():
    result = CliRunner().invoke(main, ["doctor"])

    assert result.exit_code == 0
    assert "chatup 0.2.13 ok" in result.output
