import importlib.util

import click
from click.testing import CliRunner

from chatup.cli import main

BACKEND_COMMANDS = {"install", "list", "show", "path", "doctor", "remove", "gc"}


def test_browser_artifacts_have_independent_top_level_backends():
    commands = set(main.commands)

    assert "chrome-for-testing" in commands
    assert "chromedriver" in commands
    assert "chrome" not in commands
    assert "browser" not in commands
    assert "chromium" not in commands


def test_each_implemented_backend_owns_its_command_set():
    runner = CliRunner()

    for backend in ("chrome-for-testing", "chromedriver"):
        command = main.commands[backend]
        assert isinstance(command, click.Group)
        assert set(command.commands) == BACKEND_COMMANDS

        result = runner.invoke(main, [backend, "--help"])
        assert result.exit_code == 0, result.output
        for child in sorted(BACKEND_COMMANDS):
            assert child in result.output


def test_user_cli_has_no_test_command():
    runner = CliRunner()

    for backend in ("chrome-for-testing", "chromedriver"):
        result = runner.invoke(main, [backend, "test", "--help"])
        assert result.exit_code != 0
        assert "No such command" in result.output


def test_ambiguous_python_surfaces_are_not_present():
    assert importlib.util.find_spec("chatup.chrome") is None
    assert importlib.util.find_spec("chatup.browser") is None
    assert importlib.util.find_spec("chatup.runtime.browser") is None
