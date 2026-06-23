from click.testing import CliRunner

from chatup import __version__
from chatup.cli import main


def test_version_present():
    assert __version__ == "0.2.0"


def test_cli_help():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "ChatUp CLI" in result.output
    assert "doctor" in result.output


def test_cli_doctor():
    result = CliRunner().invoke(main, ["doctor"])

    assert result.exit_code == 0
    assert "chatup 0.2.0 ok" in result.output
