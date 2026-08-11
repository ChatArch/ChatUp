from click.testing import CliRunner

from chatup import __version__
from chatup.cli import main


def test_version_present():
    assert __version__ == "0.2.10"


def test_cli_help():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "ChatUp CLI" in result.output
    assert "doctor" in result.output
    assert "--tree" in result.output


def test_cli_tree_lists_registered_command_surface():
    result = CliRunner().invoke(main, ["--tree"])

    assert result.exit_code == 0, result.output
    assert "chatup  # ChatUp CLI for ChatArch bootstrap workflows" in result.output
    assert "├── --help  # Show help for the current command." in result.output
    assert "├── --version  # Show package version." in result.output
    assert "├── --tree  # Print the registered CLI tree." in result.output
    for command in [
        "doctor",
        "workspace",
        "chrome-for-testing",
        "chromedriver",
        "playwright",
    ]:
        assert command in result.output
    assert "chrome-for-testing" in result.output
    assert "│   ├── install" in result.output
    assert "│   └── gc" in result.output


def test_cli_doctor():
    result = CliRunner().invoke(main, ["doctor"])

    assert result.exit_code == 0
    assert "chatup 0.2.10 ok" in result.output
