"""Official Gemini CLI and Desktop installation commands."""
from __future__ import annotations

import shlex

import click


@click.group(name="gemini")
def gemini_cli() -> None:
    """Install Google Gemini CLI or Desktop from official downloads."""


@gemini_cli.command(name="cli")
@click.option("--dry-run", is_flag=True, help="Show the plan without downloading or installing.")
def cli_install(**kwargs) -> None:
    """Install and verify Google's Gemini CLI npm package (Node.js 20+)."""
    from chatup.setup.gemini import setup_gemini_cli

    try:
        result = setup_gemini_cli(**kwargs)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if result["status"] == "planned":
        click.echo(f"Gemini CLI install plan ({result['platform']}):")
        click.echo(shlex.join(result["command"]))
        click.echo(f"Requires Node.js >= {result['minimum_node_major']} and npm (chatup nodejs).")
        click.echo("Dry run: no download or installation performed.")
        return
    status = "Already installed" if result["status"] == "already_installed" else "Installed"
    click.echo(f"{status}: Gemini CLI {result['version']}")
    click.echo(result["binary"])
    click.echo("Installation verified. Run gemini to sign in and start a session.")


@gemini_cli.command(name="desktop")
@click.option("--dry-run", is_flag=True, help="Show the plan without downloading or installing.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
def desktop_install(**kwargs) -> None:
    """Install the official Gemini Desktop App (macOS only)."""
    from chatup.commands.desktop import _install

    _install("gemini", **kwargs)
