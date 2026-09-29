"""CLI entry points for native desktop app installation."""
from __future__ import annotations

import shlex

import click


def _install(app: str, **kwargs) -> None:
    from chatup.setup.desktop import setup_desktop_app

    try:
        result = setup_desktop_app(app, **kwargs)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if result["status"] == "planned":
        click.echo(f"{result['app']} install plan ({result['platform']}):")
        if "url" in result:
            click.echo(f"Download: {result['url']}")
        if "sha256" in result:
            click.echo(f"SHA-256: {result['sha256']}")
        if "path" in result:
            click.echo(f"Install to: {result['path']} (verify publisher signature)")
        if "command" in result:
            click.echo(shlex.join(result["command"]))
        click.echo("Dry run: no download or installation performed.")
        return
    status = "Already installed" if result["status"] == "already_installed" else "Installed"
    click.echo(f"{status}: {result['app']} {result.get('version', '')}".strip())
    if "path" in result:
        click.echo(result["path"])
    elif "binary" in result:
        click.echo(result["binary"])
    click.echo("Installation verified.")


@click.command(name="chrome")
@click.option("--dry-run", is_flag=True, help="Show the installation plan without downloading or installing.")
@click.option("--sudo", is_flag=True, help="Allow sudo for Linux system package installation.")
@click.option("--yes", "-y", is_flag=True, help="Accept Windows agreements or Linux package-manager prompts.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
def chrome_cli(**kwargs) -> None:
    """Install regular Google Chrome for macOS, Windows or Linux."""
    _install("chrome", **kwargs)


@click.command(name="snipaste")
@click.option("--dry-run", is_flag=True, help="Show the installation plan without downloading or installing.")
@click.option("--yes", "-y", is_flag=True, help="Accept Windows agreements.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
def snipaste_cli(**kwargs) -> None:
    """Install Snipaste for macOS or Windows."""
    _install("snipaste", **kwargs)


@click.command(name="iterm")
@click.option("--dry-run", is_flag=True, help="Show the installation plan without downloading or installing.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
def iterm_cli(**kwargs) -> None:
    """Install iTerm2 from the official download (macOS only)."""
    _install("iterm", **kwargs)
