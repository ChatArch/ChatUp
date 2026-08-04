from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import click
from chatup.interaction import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    resolve_command_inputs,
)

import chatup.chrome_for_testing as backend

CHANNELS = ("stable", "beta", "dev", "canary")
OUTPUT_TYPES = ("text", "json")


def _validate_release(value: Any, _values: dict[str, Any]) -> str | None:
    text = str(value).strip().lower()
    if text in CHANNELS or re.fullmatch(r"\d+\.\d+\.\d+\.\d+", text):
        return None
    return "Chrome for Testing release must be a channel or four-component version"


def _validate_exact_version(value: Any, _values: dict[str, Any]) -> str | None:
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(value).strip()):
        return None
    return "Chrome for Testing version must contain four numeric components"


INSTALL_SCHEMA = CommandSchema(
    name="chrome-for-testing install",
    fields=(
        CommandField(
            "release",
            prompt="Chrome for Testing channel or exact version",
            required=True,
            default="stable",
            prompt_if_missing=True,
            normalizer=lambda value: str(value).strip().lower(),
            validator=_validate_release,
        ),
    ),
)
VERSION_SCHEMA = CommandSchema(
    name="chrome-for-testing version",
    fields=(
        CommandField(
            "version",
            prompt="Installed Chrome for Testing version",
            required=True,
            normalizer=lambda value: str(value).strip(),
            validator=_validate_exact_version,
        ),
    ),
)


def _resolve_release(
    *,
    version: str | None,
    channel: str | None,
    interactive: bool | None,
) -> str:
    if version and channel:
        raise click.ClickException("Use either --version or --channel, not both.")
    values = resolve_command_inputs(
        schema=INSTALL_SCHEMA,
        provided={"release": version or channel},
        interactive=interactive,
        usage=(
            "Usage: chatup chrome-for-testing install "
            "[--version VERSION | --channel CHANNEL] [-i|-I]"
        ),
    )
    return str(values["release"])


def _resolve_version(version: str | None, interactive: bool | None, action: str) -> str:
    values = resolve_command_inputs(
        schema=VERSION_SCHEMA,
        provided={"version": version},
        interactive=interactive,
        usage=(
            f"Usage: chatup chrome-for-testing {action} "
            "[VERSION] [-i|-I]"
        ),
    )
    return str(values["version"])


def _emit(payload: Any, output: str) -> None:
    if output.lower() == "json":
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        if not payload:
            click.echo("No Chrome for Testing installations found.")
            return
        for item in payload:
            click.echo(f"{item['ref']}\t{item['platform']}\t{item['binary_path']}")
        return
    for key, value in payload.items():
        if value is not None:
            click.echo(f"{key}: {value}")


def _call(operation):
    try:
        return operation()
    except backend.ChromeForTestingError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group(name="chrome-for-testing")
def cli() -> None:
    """Manage version-pinned Google Chrome for Testing browsers."""


@cli.command(name="install")
@click.option("--version", default=None, help="Exact four-component version.")
@click.option(
    "--channel",
    type=click.Choice(CHANNELS, case_sensitive=False),
    default=None,
    help="Google Chrome for Testing release channel.",
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
    help="Chrome for Testing backend home.",
)
@click.option(
    "--platform",
    type=click.Choice(backend.SUPPORTED_PLATFORMS, case_sensitive=False),
    default=None,
    help="Override automatic platform detection.",
)
@click.option("--sha256", "expected_sha256", default=None, help="Expected archive SHA-256.")
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
    channel: str | None,
    home: Path,
    platform: str | None,
    expected_sha256: str | None,
    force: bool,
    doctor: bool,
    output: str,
    interactive: bool | None,
) -> None:
    """Install one Chrome for Testing release."""

    release = _resolve_release(
        version=version,
        channel=channel,
        interactive=interactive,
    )
    installation = _call(
        lambda: backend.install(
            release,
            home=home,
            platform=platform,
            expected_sha256=expected_sha256,
            force=force,
        )
    )
    health = _call(lambda: backend.doctor(installation, execute=doctor))
    _emit(health, output)
    if health["status"] != "ready":
        raise click.ClickException(
            "Chrome for Testing installation is unhealthy: "
            + ", ".join(health["errors"])
        )


@cli.command(name="list")
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
def list_command(home: Path, output: str) -> None:
    """List valid managed Chrome for Testing installations."""

    installations = _call(lambda: backend.list_installations(home=home))
    _emit([item.to_dict() for item in installations], output)


@cli.command(name="show")
@click.argument("version", required=False)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--platform",
    type=click.Choice(backend.SUPPORTED_PLATFORMS, case_sensitive=False),
    default=None,
)
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
@add_interactive_option
def show_command(
    version: str | None,
    home: Path,
    platform: str | None,
    output: str,
    interactive: bool | None,
) -> None:
    """Show one exact installation descriptor."""

    exact = _resolve_version(version, interactive, "show")
    installation = _call(
        lambda: backend.resolve(exact, home=home, platform=platform)
    )
    _emit(installation.to_dict(), output)


@cli.command(name="path")
@click.argument("version", required=False)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--platform",
    type=click.Choice(backend.SUPPORTED_PLATFORMS, case_sensitive=False),
    default=None,
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
    home: Path,
    platform: str | None,
    output: str,
    interactive: bool | None,
) -> None:
    """Print the executable path for one exact version."""

    exact = _resolve_version(version, interactive, "path")
    installation = _call(
        lambda: backend.resolve(exact, home=home, platform=platform)
    )
    if output.lower() == "json":
        _emit(
            {
                "kind": installation.kind,
                "version": installation.version,
                "platform": installation.platform,
                "binary_path": str(installation.binary_path),
            },
            output,
        )
    else:
        click.echo(installation.binary_path)


@cli.command(name="doctor")
@click.argument("version", required=False)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--platform",
    type=click.Choice(backend.SUPPORTED_PLATFORMS, case_sensitive=False),
    default=None,
)
@click.option(
    "--execute/--no-execute",
    default=True,
    show_default=True,
    help="Run the executable version probe.",
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
    home: Path,
    platform: str | None,
    execute: bool,
    output: str,
    interactive: bool | None,
) -> None:
    """Validate one installed Chrome for Testing browser."""

    exact = _resolve_version(version, interactive, "doctor")
    installation = _call(
        lambda: backend.resolve(exact, home=home, platform=platform)
    )
    health = _call(lambda: backend.doctor(installation, execute=execute))
    _emit(health, output)
    if health["status"] != "ready":
        raise click.ClickException(
            "Chrome for Testing installation is unhealthy: "
            + ", ".join(health["errors"])
        )


@cli.command(name="remove")
@click.argument("version", required=False)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--platform",
    type=click.Choice(backend.SUPPORTED_PLATFORMS, case_sensitive=False),
    default=None,
)
@click.option("--yes", is_flag=True, help="Confirm permanent removal.")
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
@add_interactive_option
def remove_command(
    version: str | None,
    home: Path,
    platform: str | None,
    yes: bool,
    output: str,
    interactive: bool | None,
) -> None:
    """Remove one exact managed installation."""

    if not yes:
        raise click.ClickException("Refusing to remove without --yes.")
    exact = _resolve_version(version, interactive, "remove")
    installation = _call(
        lambda: backend.remove(exact, home=home, platform=platform)
    )
    _emit(
        {
            "kind": installation.kind,
            "version": installation.version,
            "platform": installation.platform,
            "removed_root": str(installation.root_dir),
            "status": "removed",
        },
        output,
    )


@cli.command(name="gc")
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False),
    default=backend.DEFAULT_HOME,
    show_default=True,
)
@click.option(
    "--dry-run/--apply",
    default=True,
    show_default=True,
    help="Preview stale temporary directories or remove them.",
)
@click.option("--yes", is_flag=True, help="Confirm removal when --apply is used.")
@click.option(
    "--minimum-age-hours",
    type=click.IntRange(min=1),
    default=24,
    show_default=True,
)
@click.option(
    "--output",
    type=click.Choice(OUTPUT_TYPES, case_sensitive=False),
    default="text",
    show_default=True,
)
def gc_command(
    home: Path,
    dry_run: bool,
    yes: bool,
    minimum_age_hours: int,
    output: str,
) -> None:
    """Preview or remove stale backend temporary directories."""

    if not dry_run and not yes:
        raise click.ClickException("Refusing to apply garbage collection without --yes.")
    result = _call(
        lambda: backend.gc(
            home=home,
            dry_run=dry_run,
            yes=yes,
            minimum_age_seconds=minimum_age_hours * 60 * 60,
        )
    )
    _emit(result, output)
