"""Public API for ChatArch-managed Chrome installations."""

from chatup.setup.chrome import (
    ChromeInstallError,
    ChromeInstallation,
    DEFAULT_CHROME_HOME,
    SUPPORTED_CFT_PLATFORMS,
    ensure_chrome,
    install_chrome,
    resolve_chrome,
)

__all__ = [
    "ChromeInstallError",
    "ChromeInstallation",
    "DEFAULT_CHROME_HOME",
    "SUPPORTED_CFT_PLATFORMS",
    "ensure_chrome",
    "install_chrome",
    "resolve_chrome",
]
