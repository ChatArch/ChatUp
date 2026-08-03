from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chatup.setup.nodejs import MIN_NODEJS_MAJOR, _detect_nodejs_runtime

from ._managed_artifact import (
    ManagedArtifactError,
    atomic_write_json,
    replace_directory,
)

PLAYWRIGHT = "playwright"
DEFAULT_PLAYWRIGHT_HOME = Path.home() / ".chatarch" / PLAYWRIGHT
METADATA_NAME = "installation.json"
SUPPORTED_PLAYWRIGHT_BROWSERS = ("chromium",)


class PlaywrightError(RuntimeError):
    """Raised when a Playwright-managed browser cannot be resolved safely."""


@dataclass(frozen=True)
class PlaywrightBrowserInstallation:
    kind: str
    playwright_version: str
    browser: str
    browser_revision: str
    browser_version: str
    root_dir: Path
    package_dir: Path
    browsers_dir: Path
    binary_path: Path
    node_version: str
    installed_at: str

    @property
    def ref(self) -> str:
        return f"{self.kind}@{self.playwright_version}/{self.browser}"

    def to_dict(self) -> dict[str, str]:
        return {
            "ref": self.ref,
            "kind": self.kind,
            "playwright_version": self.playwright_version,
            "browser": self.browser,
            "browser_revision": self.browser_revision,
            "browser_version": self.browser_version,
            "root_dir": str(self.root_dir),
            "package_dir": str(self.package_dir),
            "browsers_dir": str(self.browsers_dir),
            "binary_path": str(self.binary_path),
            "node_version": self.node_version,
            "installed_at": self.installed_at,
        }


@dataclass(frozen=True)
class _InstalledPayload:
    browser_revision: str
    browser_version: str
    binary_path: Path
    node_version: str


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
Installer = Callable[..., _InstalledPayload]
RuntimeResolver = Callable[[], dict[str, Any]]


def _run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 900,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _validate_version(version: str) -> str:
    normalized = version.strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", normalized):
        raise PlaywrightError(
            "Playwright version must be an exact three-component version, "
            f"got: {version}"
        )
    return normalized


def _validate_browser(browser: str) -> str:
    normalized = browser.strip().lower()
    if normalized not in SUPPORTED_PLAYWRIGHT_BROWSERS:
        raise PlaywrightError(
            f"Unsupported Playwright browser: {browser}; "
            f"expected one of {', '.join(SUPPORTED_PLAYWRIGHT_BROWSERS)}"
        )
    return normalized


def _resolve_node_runtime(runtime_resolver: RuntimeResolver) -> dict[str, Any]:
    runtime = runtime_resolver()
    node_bin = runtime.get("node_bin")
    npm_bin = runtime.get("npm_bin")
    node_major = runtime.get("node_major")
    if not node_bin or not npm_bin or not isinstance(node_major, int):
        raise PlaywrightError(
            "Node.js and npm are required for Playwright; run `chatup nodejs` first"
        )
    if node_major < MIN_NODEJS_MAJOR:
        raise PlaywrightError(
            f"Playwright requires Node.js >= {MIN_NODEJS_MAJOR}; "
            f"found {runtime.get('node_version') or 'unknown'}"
        )
    return runtime


def _command_env(runtime: dict[str, Any], browsers_dir: Path) -> dict[str, str]:
    env = dict(os.environ)
    node_bin = Path(str(runtime["node_bin"]))
    env["PATH"] = str(node_bin.parent) + os.pathsep + env.get("PATH", "")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_dir)
    env["PLAYWRIGHT_SKIP_BROWSER_GC"] = "1"
    return env


def _raise_command_error(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    if len(detail) > 4000:
        detail = detail[-4000:]
    raise PlaywrightError(
        f"{action} failed with exit code {result.returncode}"
        + (f": {detail}" if detail else "")
    )


def _install_with_npm(
    version: str,
    browser: str,
    staging_dir: Path,
    *,
    runtime: dict[str, Any],
    runner: CommandRunner = _run_command,
) -> _InstalledPayload:
    package_dir = staging_dir / "package"
    browsers_dir = staging_dir / "browsers"
    package_dir.mkdir(parents=True)
    browsers_dir.mkdir(parents=True)
    env = _command_env(runtime, browsers_dir)

    npm_result = runner(
        [
            str(runtime["npm_bin"]),
            "install",
            "--prefix",
            str(package_dir),
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            f"playwright@{version}",
        ],
        cwd=staging_dir,
        env=env,
        timeout=600,
    )
    _raise_command_error(npm_result, "Playwright npm install")

    package_metadata = package_dir / "node_modules" / "playwright" / "package.json"
    core_manifest = package_dir / "node_modules" / "playwright-core" / "browsers.json"
    playwright_cli = package_dir / "node_modules" / "playwright" / "cli.js"
    if not package_metadata.is_file() or not core_manifest.is_file() or not playwright_cli.is_file():
        raise PlaywrightError("Playwright npm installation is incomplete")

    package_payload = json.loads(package_metadata.read_text(encoding="utf-8"))
    if package_payload.get("version") != version:
        raise PlaywrightError(
            f"Installed Playwright version mismatch: {package_payload.get('version')}"
        )

    install_result = runner(
        [str(runtime["node_bin"]), str(playwright_cli), "install", browser],
        cwd=package_dir,
        env=env,
        timeout=900,
    )
    _raise_command_error(install_result, f"Playwright {browser} install")

    manifest = json.loads(core_manifest.read_text(encoding="utf-8"))
    entries = manifest.get("browsers")
    entry = next(
        (
            item
            for item in entries
            if isinstance(item, dict) and item.get("name") == browser
        ),
        None,
    ) if isinstance(entries, list) else None
    if not isinstance(entry, dict):
        raise PlaywrightError(f"Playwright manifest does not declare browser: {browser}")
    revision = str(entry.get("revision") or "")
    browser_version = str(entry.get("browserVersion") or "")
    if not revision.isdigit() or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", browser_version):
        raise PlaywrightError("Playwright browser manifest contains invalid identity data")

    module_path = package_dir / "node_modules" / "playwright"
    resolver_script = (
        "const { chromium } = require(" + json.dumps(str(module_path)) + ");"
        "process.stdout.write(chromium.executablePath());"
    )
    resolve_result = runner(
        [str(runtime["node_bin"]), "-e", resolver_script],
        cwd=package_dir,
        env=env,
        timeout=60,
    )
    _raise_command_error(resolve_result, "Playwright browser path resolution")
    binary_path = Path(resolve_result.stdout.strip()).expanduser().resolve()
    staging_resolved = staging_dir.resolve()
    if not binary_path.is_file() or not binary_path.is_relative_to(staging_resolved):
        raise PlaywrightError(
            f"Playwright resolved a browser outside the managed installation: {binary_path}"
        )

    return _InstalledPayload(
        browser_revision=revision,
        browser_version=browser_version,
        binary_path=binary_path,
        node_version=str(runtime.get("node_version") or ""),
    )


def install_playwright_browser(
    version: str,
    *,
    browser: str = "chromium",
    home: Path | str | None = None,
    force: bool = False,
    runtime_resolver: RuntimeResolver = _detect_nodejs_runtime,
    installer: Installer = _install_with_npm,
) -> PlaywrightBrowserInstallation:
    exact_version = _validate_version(version)
    browser_name = _validate_browser(browser)
    home_path = Path(home).expanduser() if home is not None else DEFAULT_PLAYWRIGHT_HOME
    install_dir = home_path / exact_version / browser_name
    if install_dir.is_symlink():
        raise PlaywrightError(
            f"Refusing to use a symlink as a Playwright installation root: {install_dir}"
        )
    _validate_install_location(home_path, install_dir)
    metadata_path = install_dir / METADATA_NAME

    if metadata_path.is_file() and not force:
        return load_playwright_browser(metadata_path)
    if install_dir.exists() and not force:
        raise PlaywrightError(
            f"Playwright directory exists without valid metadata: {install_dir}; "
            "use force to replace it"
        )

    runtime = _resolve_node_runtime(runtime_resolver)
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{browser_name}-install-",
        dir=install_dir.parent,
    ) as temporary:
        temporary_dir = Path(temporary)
        staging_dir = temporary_dir / "installation"
        staging_dir.mkdir()
        payload = installer(
            exact_version,
            browser_name,
            staging_dir,
            runtime=runtime,
        )
        binary_relative = payload.binary_path.resolve().relative_to(staging_dir.resolve())
        installation = PlaywrightBrowserInstallation(
            kind=PLAYWRIGHT,
            playwright_version=exact_version,
            browser=browser_name,
            browser_revision=payload.browser_revision,
            browser_version=payload.browser_version,
            root_dir=install_dir,
            package_dir=install_dir / "package",
            browsers_dir=install_dir / "browsers",
            binary_path=install_dir / binary_relative,
            node_version=payload.node_version,
            installed_at=datetime.now(timezone.utc).isoformat(),
        )
        atomic_write_json(staging_dir / METADATA_NAME, installation.to_dict())
        try:
            replace_directory(staging_dir, install_dir)
        except (OSError, ManagedArtifactError) as exc:
            raise PlaywrightError(f"Failed to install Playwright atomically: {exc}") from exc

    return load_playwright_browser(metadata_path)


def load_playwright_browser(
    metadata_path: Path | str,
) -> PlaywrightBrowserInstallation:
    path = Path(metadata_path)
    if path.is_symlink() or not path.is_file():
        raise PlaywrightError(f"Playwright metadata is missing or unsafe: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlaywrightError(f"Invalid Playwright metadata: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlaywrightError(f"Playwright metadata is not an object: {path}")

    string_fields = (
        "kind",
        "playwright_version",
        "browser",
        "browser_revision",
        "browser_version",
        "root_dir",
        "package_dir",
        "browsers_dir",
        "binary_path",
        "node_version",
        "installed_at",
    )
    if any(not isinstance(payload.get(field), str) or not payload[field] for field in string_fields):
        raise PlaywrightError(f"Playwright metadata contains invalid fields: {path}")
    if payload["kind"] != PLAYWRIGHT:
        raise PlaywrightError(f"Unexpected Playwright metadata kind: {payload['kind']}")
    _validate_version(payload["playwright_version"])
    _validate_browser(payload["browser"])
    if not payload["browser_revision"].isdigit():
        raise PlaywrightError("Playwright metadata contains an invalid browser revision")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", payload["browser_version"]):
        raise PlaywrightError("Playwright metadata contains an invalid browser version")

    root_dir = path.parent.resolve()
    if Path(payload["root_dir"]).expanduser().resolve() != root_dir:
        raise PlaywrightError("Playwright metadata root does not match its installation")
    package_dir = Path(payload["package_dir"]).expanduser().resolve()
    browsers_dir = Path(payload["browsers_dir"]).expanduser().resolve()
    binary_path = Path(payload["binary_path"]).expanduser().resolve()
    for managed_path in (package_dir, browsers_dir, binary_path):
        if not managed_path.is_relative_to(root_dir):
            raise PlaywrightError(
                f"Playwright metadata path escapes its installation: {managed_path}"
            )
    if not package_dir.is_dir() or not browsers_dir.is_dir() or not binary_path.is_file():
        raise PlaywrightError("Playwright installation files are missing")

    return PlaywrightBrowserInstallation(
        kind=payload["kind"],
        playwright_version=payload["playwright_version"],
        browser=payload["browser"],
        browser_revision=payload["browser_revision"],
        browser_version=payload["browser_version"],
        root_dir=root_dir,
        package_dir=package_dir,
        browsers_dir=browsers_dir,
        binary_path=binary_path,
        node_version=payload["node_version"],
        installed_at=payload["installed_at"],
    )


def resolve_playwright_browser(
    version: str,
    *,
    browser: str = "chromium",
    home: Path | str | None = None,
) -> PlaywrightBrowserInstallation:
    exact_version = _validate_version(version)
    browser_name = _validate_browser(browser)
    home_path = Path(home).expanduser() if home is not None else DEFAULT_PLAYWRIGHT_HOME
    install_dir = home_path / exact_version / browser_name
    _validate_install_location(home_path, install_dir)
    metadata_path = install_dir / METADATA_NAME
    if not metadata_path.is_file():
        raise PlaywrightError(
            f"Playwright browser is not installed: {exact_version}/{browser_name}"
        )
    return load_playwright_browser(metadata_path)


def doctor_playwright_browser(
    installation: PlaywrightBrowserInstallation,
    *,
    execute: bool = True,
    runner: CommandRunner = _run_command,
) -> dict[str, Any]:
    errors: list[str] = []
    if not installation.binary_path.is_file():
        errors.append("binary_missing")
    if not installation.package_dir.is_dir():
        errors.append("package_missing")
    observed_version: str | None = None
    if execute and not errors:
        try:
            result = runner(
                [str(installation.binary_path), "--version"],
                cwd=installation.root_dir,
                env=dict(os.environ),
                timeout=30,
            )
            if result.returncode != 0:
                errors.append("execution_failed")
            else:
                observed_version = result.stdout.strip()
                if installation.browser_version not in observed_version:
                    errors.append("version_mismatch")
        except Exception:  # noqa: BLE001 - doctor reports probe failures as health data.
            errors.append("execution_failed")
    return {
        **installation.to_dict(),
        "status": "ready" if not errors else "unhealthy",
        "errors": errors,
        "observed_version": observed_version,
    }


def _validate_install_location(home: Path, install_dir: Path) -> None:
    home_resolved = home.expanduser().resolve()
    install_resolved = install_dir.expanduser().resolve()
    if not install_resolved.is_relative_to(home_resolved):
        raise PlaywrightError(
            f"Playwright installation escapes its managed home: {install_dir}"
        )
