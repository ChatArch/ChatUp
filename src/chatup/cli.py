from __future__ import annotations

import click

from chatup import __version__
from chatup.setup.cli import register_setup_commands


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="chatup")
def main() -> None:
    """ChatUp CLI for ChatArch bootstrap workflows."""


@main.command(name="doctor")
def doctor() -> None:
    """Check that ChatUp is installed and callable."""
    click.echo(f"chatup {__version__} ok")


register_setup_commands(main)


if __name__ == "__main__":
    main()
