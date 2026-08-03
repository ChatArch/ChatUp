from __future__ import annotations

import json
from pathlib import Path

import click

from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.runtime.browser import (
    BrowserRuntime as ChromeInstallation,
    BrowserRuntimeError as ChromeInstallError,
    DEFAULT_BROWSER_HOME as DEFAULT_CHROME_HOME,
    SUPPORTED_CFT_PLATFORMS,
    doctor_browser_runtime,
    ensure_chrome_for_testing,
    install_chrome_for_testing,
    resolve_browser_runtime,
)


def install_chrome(
    version: str = "stable",
    *,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
) -> ChromeInstallation:
    """Install one ChatArch-managed Chrome for Testing build."""

    return install_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
        expected_sha256=expected_sha256,
        force=force,
    )


def ensure_chrome(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
) -> ChromeInstallation:
    """Resolve an exact build or install it when missing."""

    return ensure_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
        expected_sha256=expected_sha256,
    )


def resolve_chrome(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
) -> ChromeInstallation:
    """Resolve an installed exact Chrome build without network access."""

    return resolve_browser_runtime(
        f"chrome-for-testing@{version}",
        home=home,
        cft_platform=platform,
    )


def setup_chrome(
    *,
    version: str = "stable",
    home: Path | str = DEFAULT_CHROME_HOME,
    platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
    doctor: bool = True,
    output: str = "text",
    interactive: bool | None = None,
) -> ChromeInstallation:
    """Install Chrome and emit a stable human or JSON result."""

    usage = "Usage: chatup chrome [OPTIONS]"
    _, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    runtime = install_chrome(
        version,
        home=home,
        platform=platform,
        expected_sha256=expected_sha256,
        force=force,
    )
    health = doctor_browser_runtime(runtime, execute=doctor)

    if output.lower() == "json":
        click.echo(json.dumps(health, indent=2, sort_keys=True))
    else:
        click.echo(f"Chrome: {runtime.ref}")
        click.echo(f"Platform: {runtime.platform}")
        click.echo(f"Binary: {runtime.binary_path}")
        click.echo(f"Home: {runtime.root_dir}")
        click.echo(f"Status: {health['status']}")
        if health.get("reported_version"):
            click.echo(f"Reported version: {health['reported_version']}")

    if health["status"] != "ready":
        details = ", ".join(health["errors"])
        raise click.ClickException(f"Chrome installation is unhealthy: {details}")
    return runtime


__all__ = [
    "ChromeInstallation",
    "ChromeInstallError",
    "DEFAULT_CHROME_HOME",
    "SUPPORTED_CFT_PLATFORMS",
    "ensure_chrome",
    "install_chrome",
    "resolve_chrome",
    "setup_chrome",
]
