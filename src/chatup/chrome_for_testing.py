"""Public API for ChatArch-managed Google Chrome for Testing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chatup.runtime.chrome_for_testing import (
    DEFAULT_CHROME_FOR_TESTING_HOME,
    SUPPORTED_CFT_PLATFORMS,
    ChromeForTestingError,
    ChromeForTestingInstallation,
    doctor_chrome_for_testing,
    ensure_chrome_for_testing,
    garbage_collect_chrome_for_testing,
    install_chrome_for_testing,
    list_chrome_for_testing,
    remove_chrome_for_testing,
    resolve_chrome_for_testing,
)

DEFAULT_HOME = DEFAULT_CHROME_FOR_TESTING_HOME
SUPPORTED_PLATFORMS = SUPPORTED_CFT_PLATFORMS


def install(
    version: str = "stable",
    *,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
) -> ChromeForTestingInstallation:
    return install_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
        expected_sha256=expected_sha256,
        force=force,
    )


def ensure(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
    expected_sha256: str | None = None,
) -> ChromeForTestingInstallation:
    return ensure_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
        expected_sha256=expected_sha256,
    )


def resolve(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
) -> ChromeForTestingInstallation:
    return resolve_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
    )


def list_installations(
    *,
    home: Path | str | None = None,
) -> list[ChromeForTestingInstallation]:
    return list_chrome_for_testing(home=home)


def doctor(
    installation: ChromeForTestingInstallation,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    return doctor_chrome_for_testing(installation, execute=execute)


def remove(
    version: str,
    *,
    home: Path | str | None = None,
    platform: str | None = None,
) -> ChromeForTestingInstallation:
    return remove_chrome_for_testing(
        version,
        home=home,
        cft_platform=platform,
    )


def gc(
    *,
    home: Path | str | None = None,
    dry_run: bool = True,
    yes: bool = False,
    minimum_age_seconds: int = 24 * 60 * 60,
) -> dict[str, Any]:
    return garbage_collect_chrome_for_testing(
        home=home,
        dry_run=dry_run,
        yes=yes,
        minimum_age_seconds=minimum_age_seconds,
    )


__all__ = [
    "DEFAULT_HOME",
    "SUPPORTED_PLATFORMS",
    "ChromeForTestingError",
    "ChromeForTestingInstallation",
    "doctor",
    "ensure",
    "gc",
    "install",
    "list_installations",
    "remove",
    "resolve",
]
