"""Public API for ChatArch-managed Playwright browsers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chatup.runtime.playwright import (
    DEFAULT_PLAYWRIGHT_HOME,
    SUPPORTED_PLAYWRIGHT_BROWSERS,
    PlaywrightBrowserInstallation,
    PlaywrightError,
    doctor_playwright_browser,
    install_playwright_browser,
    resolve_playwright_browser,
)

DEFAULT_HOME = DEFAULT_PLAYWRIGHT_HOME
SUPPORTED_BROWSERS = SUPPORTED_PLAYWRIGHT_BROWSERS


def install(
    version: str,
    *,
    browser: str = "chromium",
    home: Path | str | None = None,
    force: bool = False,
) -> PlaywrightBrowserInstallation:
    return install_playwright_browser(
        version,
        browser=browser,
        home=home,
        force=force,
    )


def resolve(
    version: str,
    *,
    browser: str = "chromium",
    home: Path | str | None = None,
) -> PlaywrightBrowserInstallation:
    return resolve_playwright_browser(version, browser=browser, home=home)


def doctor(
    installation: PlaywrightBrowserInstallation,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    return doctor_playwright_browser(installation, execute=execute)


__all__ = [
    "DEFAULT_HOME",
    "SUPPORTED_BROWSERS",
    "PlaywrightBrowserInstallation",
    "PlaywrightError",
    "doctor",
    "install",
    "resolve",
]
