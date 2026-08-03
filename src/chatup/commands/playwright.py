from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import click
from chatstyle import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    resolve_command_inputs,
)

import chatup.playwright as backend

OUTPUT_TYPES = ("text", "json")


def _validate_version(value: Any, _values: dict[str, Any]) -> str | None:
    if re.fullmatch(r"\d+\.\d+\.\d+", str(value).strip()):
        return None
    return "Playwright version must contain three numeric components"


VERSION_SCHEMA = CommandSchema(
    name="playwright version",
    fields=(
        CommandField(
            "version",
            prompt="Exact Playwright version",
            required=True,
            normalizer=lambda value: str(value).strip(),
            validator=_validate_version,
        ),
    ),
)


def _resolve_version(version: str | None, interactive: bool | None, action: str) -> str:
    values = resolve_command_inputs(
        schema=VERSION_SCHEMA,
        provided={"version": version},
        interactive=interactive,
        usage=f"Usage: chatup playwright {action} [VERSION] [-i|-I]",
    )
    return str(values["version"])


def _call(operation):
    try:
        return operation()
    except backend.PlaywrightError as exc:
        raise click.ClickException(str(exc)) from exc


def _emit(payload: dict[str, Any], output: str) -> None:
    if output.lower() == "json":
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if value is not None:
            click.echo(f"{key}: {value}")


@click.group(name="playwright")
def cli() -> None:
    """Manage user-level Playwright browser installations."""


@cli.command(name="install")
@click.argument("version", required=False)
@click.option(
    "--browser",
    type=click.Choice(backend.SUPPORTED_BROWSERS, case_sensitive=False),
    default="chromium",
    show_default=True,
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option("--force", is_flag=True, help="Atomically replace an existing installation.")
@click.option(
    "--doctor/--no-doctor",
    default=True,
    show_default=True,
    help="Probe the installed browser version.",
)
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
@add_interactive_option
def install_command(
    version: str | None,
    browser: str,
    home: Path,
    force: bool,
    doctor: bool,
    output: str,
    interactive: bool | None,
) -> None:
    """Install one exact Playwright package and browser."""

    exact = _resolve_version(version, interactive, "install")
    installation = _call(
        lambda: backend.install(
            exact,
            browser=browser,
            home=home,
            force=force,
        )
    )
    health = _call(lambda: backend.doctor(installation, execute=doctor))
    _emit(health, output)
    if health["status"] != "ready":
        raise click.ClickException(
            "Playwright installation is unhealthy: " + ", ".join(health["errors"])
        )


@cli.command(name="path")
@click.argument("version", required=False)
@click.option(
    "--browser",
    type=click.Choice(backend.SUPPORTED_BROWSERS, case_sensitive=False),
    default="chromium",
    show_default=True,
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
@add_interactive_option
def path_command(
    version: str | None,
    browser: str,
    home: Path,
    output: str,
    interactive: bool | None,
) -> None:
    """Print the browser executable path for an installed Playwright version."""

    exact = _resolve_version(version, interactive, "path")
    installation = _call(
        lambda: backend.resolve(exact, browser=browser, home=home)
    )
    if output.lower() == "json":
        _emit(installation.to_dict(), output)
    else:
        click.echo(installation.binary_path)


@cli.command(name="doctor")
@click.argument("version", required=False)
@click.option(
    "--browser",
    type=click.Choice(backend.SUPPORTED_BROWSERS, case_sensitive=False),
    default="chromium",
    show_default=True,
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--execute/--no-execute",
    default=True,
    show_default=True,
)
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
@add_interactive_option
def doctor_command(
    version: str | None,
    browser: str,
    home: Path,
    execute: bool,
    output: str,
    interactive: bool | None,
) -> None:
    """Validate one installed Playwright browser."""

    exact = _resolve_version(version, interactive, "doctor")
    installation = _call(
        lambda: backend.resolve(exact, browser=browser, home=home)
    )
    health = _call(lambda: backend.doctor(installation, execute=execute))
    _emit(health, output)
    if health["status"] != "ready":
        raise click.ClickException(
            "Playwright installation is unhealthy: " + ", ".join(health["errors"])
        )
