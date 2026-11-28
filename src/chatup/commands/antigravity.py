"""Official Antigravity CLI and Desktop installation commands."""
from __future__ import annotations

from pathlib import Path

import click


@click.group(name="antigravity")
def antigravity_cli() -> None:
    """Install Google Antigravity CLI or Desktop from official downloads."""


@antigravity_cli.command(name="cli")
@click.option("--dry-run", is_flag=True, help="Show the plan without downloading or installing.")
@click.option("--install-dir", type=click.Path(path_type=Path, file_okay=False), help="Directory for the agy binary (default: official user install location).")
def cli_install(**kwargs) -> None:
    """Install and verify the Antigravity terminal client (agy)."""
    from chatup.setup.antigravity import setup_antigravity_cli

    try:
        result = setup_antigravity_cli(**kwargs)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if result["status"] == "planned":
        click.echo(f"Antigravity CLI install plan ({result['platform']}):")
        click.echo(f"Official installer: {result['url']}")
        click.echo(f"Install to: {result['binary']}")
        click.echo("Dry run: no download or installation performed.")
        return
    status = "Already installed" if result["status"] == "already_installed" else "Installed"
    click.echo(f"{status}: Antigravity CLI {result['version']}")
    click.echo(result["binary"])
    click.echo("Installation verified. Run agy to sign in and start a session.")


@antigravity_cli.command(name="desktop")
@click.option("--dry-run", is_flag=True, help="Show the plan without downloading or installing.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
def desktop_install(**kwargs) -> None:
    """Install the official Antigravity Desktop App (macOS only)."""
    from chatup.commands.desktop import _install

    _install("antigravity", **kwargs)
