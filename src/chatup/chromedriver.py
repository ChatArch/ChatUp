"""Public API for ChatArch-managed ChromeDriver installations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chatup.runtime.chromedriver import (
    DEFAULT_CHROMEDRIVER_HOME,
    SUPPORTED_CHROMEDRIVER_PLATFORMS,
    ChromeDriverError,
    ChromeDriverInstallation,
    doctor_chromedriver,
    ensure_chromedriver,
    garbage_collect_chromedriver,
    install_chromedriver,
    list_chromedrivers,
    read_browser_version,
    remove_chromedriver,
    resolve_chromedriver,
    resolve_chromedriver_for_browser_version,
)

DEFAULT_HOME = DEFAULT_CHROMEDRIVER_HOME
SUPPORTED_PLATFORMS = SUPPORTED_CHROMEDRIVER_PLATFORMS


def install(
    version: str | None = None,
    *,
    match_browser: Path | str | None = None,
    match_cft_version: str | None = None,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
) -> ChromeDriverInstallation:
    return install_chromedriver(
        version,
        match_browser=match_browser,
        match_cft_version=match_cft_version,
        home=home,
        driver_platform=platform,
        expected_sha256=expected_sha256,
        force=force,
    )


def ensure(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
) -> ChromeDriverInstallation:
    return ensure_chromedriver(
        version,
        home=home,
        driver_platform=platform,
        expected_sha256=expected_sha256,
    )


def resolve(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
) -> ChromeDriverInstallation:
    return resolve_chromedriver(
        version,
        home=home,
        driver_platform=platform,
    )


def resolve_for_browser_version(
    browser_version: str,
    *,
    platform: str | None = None,
) -> tuple[str, str, str]:
    """Resolve the official compatible ChromeDriver artifact for a browser."""

    return resolve_chromedriver_for_browser_version(
        browser_version,
        driver_platform=platform,
    )


def list_installations(
    *,
    home: Path | str | None = None,
) -> list[ChromeDriverInstallation]:
    return list_chromedrivers(home=home)


def doctor(
    installation: ChromeDriverInstallation,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    return doctor_chromedriver(installation, execute=execute)


def remove(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
) -> ChromeDriverInstallation:
    return remove_chromedriver(
        version,
        home=home,
        driver_platform=platform,
    )


def gc(
    *,
    home: Path | str | None = None,
    dry_run: bool = True,
    yes: bool = False,
    minimum_age_seconds: int = 24 * 60 * 60,
) -> dict[str, Any]:
    return garbage_collect_chromedriver(
        home=home,
        dry_run=dry_run,
        yes=yes,
        minimum_age_seconds=minimum_age_seconds,
    )


__all__ = [
    "DEFAULT_HOME",
    "SUPPORTED_PLATFORMS",
    "ChromeDriverError",
    "ChromeDriverInstallation",
    "doctor",
    "ensure",
    "gc",
    "install",
    "list_installations",
    "read_browser_version",
    "remove",
    "resolve",
    "resolve_for_browser_version",
]
