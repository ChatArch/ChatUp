from __future__ import annotations

import json
import os
import platform as platform_module
import re
import stat
import subprocess
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ._managed_artifact import (
    MAX_ARCHIVE_BYTES,
    ManagedArtifactError,
    atomic_write_json,
    find_stale_directories,
    normalize_sha256,
    remove_managed_directory,
    replace_directory,
    safe_extract_zip,
    sha256_file,
)

CHROME_FOR_TESTING = "chrome-for-testing"
CFT_CHANNELS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
CFT_VERSIONS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "known-good-versions-with-downloads.json"
)
DEFAULT_CHROME_FOR_TESTING_HOME = Path.home() / ".chatarch" / CHROME_FOR_TESTING
METADATA_NAME = "installation.json"
SUPPORTED_CFT_PLATFORMS = ("linux64", "mac-arm64", "mac-x64", "win64")
CFT_DOWNLOAD_HOST = "storage.googleapis.com"
CFT_DOWNLOAD_PREFIX = "/chrome-for-testing-public/"


class ChromeForTestingError(RuntimeError):
    """Raised when Chrome for Testing cannot be managed safely."""


@dataclass(frozen=True)
class ChromeForTestingInstallation:
    kind: str
    version: str
    platform: str
    root_dir: Path
    binary_path: Path
    source_url: str
    archive_sha256: str
    installed_at: str

    @property
    def ref(self) -> str:
        return f"{self.kind}@{self.version}"

    def to_dict(self) -> dict[str, str]:
        return {
            "ref": self.ref,
            "kind": self.kind,
            "version": self.version,
            "platform": self.platform,
            "root_dir": str(self.root_dir),
            "binary_path": str(self.binary_path),
            "source_url": self.source_url,
            "archive_sha256": self.archive_sha256,
            "installed_at": self.installed_at,
        }


def normalize_cft_platform(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    system_name = (system or platform_module.system()).strip().lower()
    machine_name = (machine or platform_module.machine()).strip().lower()

    if system_name == "darwin":
        if machine_name in {"arm64", "aarch64"}:
            return "mac-arm64"
        if machine_name in {"x86_64", "amd64"}:
            return "mac-x64"
    elif system_name == "linux" and machine_name in {"x86_64", "amd64"}:
        return "linux64"
    elif system_name == "windows" and machine_name in {"x86_64", "amd64"}:
        return "win64"

    raise ChromeForTestingError(
        f"Chrome for Testing does not provide a supported build for "
        f"system={system_name!r}, machine={machine_name!r}"
    )


def fetch_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatUp/chrome-for-testing"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:
        raise ChromeForTestingError(
            f"Failed to fetch Chrome for Testing manifest: {url}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ChromeForTestingError(
            f"Chrome for Testing manifest is not an object: {url}"
        )
    return payload


def download_file(url: str, destination: Path, *, timeout: float = 120.0) -> None:
    _validate_download_url(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatUp/chrome-for-testing"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise ChromeForTestingError("Chrome for Testing archive exceeds the 1 GiB download limit")
            with destination.open("wb") as output:
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_ARCHIVE_BYTES:
                        raise ChromeForTestingError("Chrome for Testing archive exceeds the 1 GiB download limit")
                    output.write(chunk)
    except Exception as exc:
        raise ChromeForTestingError(
            f"Failed to download Chrome for Testing archive: {url}: {exc}"
        ) from exc


def resolve_chrome_for_testing_download(
    version: str = "stable",
    *,
    cft_platform: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
) -> tuple[str, str, str]:
    requested = version.strip()
    if not requested:
        raise ChromeForTestingError("Chrome for Testing version must not be empty")
    platform_name = cft_platform or normalize_cft_platform()
    if platform_name not in SUPPORTED_CFT_PLATFORMS:
        raise ChromeForTestingError(f"Unsupported Chrome for Testing platform: {platform_name}")

    channel_names = {name.lower(): name for name in ("Stable", "Beta", "Dev", "Canary")}
    if requested.lower() in channel_names:
        data = fetcher(CFT_CHANNELS_URL)
        channels = data.get("channels")
        entry = (
            channels.get(channel_names[requested.lower()])
            if isinstance(channels, dict)
            else None
        )
    else:
        data = fetcher(CFT_VERSIONS_URL)
        versions = data.get("versions")
        entry = next(
            (
                item
                for item in versions
                if isinstance(item, dict) and item.get("version") == requested
            ),
            None,
        ) if isinstance(versions, list) else None

    if not isinstance(entry, dict) or not entry.get("version"):
        raise ChromeForTestingError(f"Chrome for Testing version not found: {requested}")

    download_groups = entry.get("downloads")
    downloads = (
        download_groups.get("chrome", [])
        if isinstance(download_groups, dict)
        else []
    )
    artifact = next(
        (
            item
            for item in downloads
            if isinstance(item, dict) and item.get("platform") == platform_name
        ),
        None,
    ) if isinstance(downloads, list) else None
    if not isinstance(artifact, dict) or not artifact.get("url"):
        raise ChromeForTestingError(
            f"Chrome for Testing {entry['version']} has no {platform_name} download"
        )

    url = str(artifact["url"])
    _validate_download_url(url)
    return str(entry["version"]), platform_name, url


def install_chrome_for_testing(
    version: str = "stable",
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
    resolver: Callable[..., tuple[str, str, str]] = resolve_chrome_for_testing_download,
    downloader: Callable[[str, Path], None] = download_file,
) -> ChromeForTestingInstallation:
    resolved_version, platform_name, source_url = resolver(
        version,
        cft_platform=cft_platform,
    )
    _validate_resolved_identity(resolved_version, platform_name)
    _validate_download_url(source_url)
    home_path = (
        Path(home).expanduser()
        if home is not None
        else DEFAULT_CHROME_FOR_TESTING_HOME
    )
    install_dir = home_path / resolved_version / platform_name
    if install_dir.is_symlink():
        raise ChromeForTestingError(
            f"Refusing to use a symlink as a Chrome for Testing installation root: {install_dir}"
        )
    _validate_install_location(home_path, install_dir)
    metadata_path = install_dir / METADATA_NAME
    normalized_expected = _normalize_sha256(expected_sha256)

    if metadata_path.is_file() and not force:
        runtime = load_chrome_for_testing(metadata_path)
        if normalized_expected and runtime.archive_sha256 != normalized_expected:
            raise ChromeForTestingError(
                "Installed Chrome for Testing SHA-256 does not match the expected archive digest"
            )
        return runtime
    if install_dir.exists() and not force:
        raise ChromeForTestingError(
            f"Chrome for Testing directory exists without valid metadata: {install_dir}; use force to replace it"
        )

    install_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".{platform_name}-install-",
        dir=install_dir.parent,
    ) as temporary:
        temporary_dir = Path(temporary)
        archive_path = temporary_dir / "chrome-for-testing.zip"
        staging_dir = temporary_dir / "installation"
        downloader(source_url, archive_path)

        archive_sha256 = _sha256_file(archive_path)
        if normalized_expected and archive_sha256 != normalized_expected:
            raise ChromeForTestingError(
                f"Chrome for Testing archive SHA-256 mismatch: expected {normalized_expected}, got {archive_sha256}"
            )

        safe_extract_chrome_for_testing_zip(archive_path, staging_dir)
        binary_relative = _binary_relative_path(platform_name)
        staged_binary = staging_dir / binary_relative
        if not staged_binary.is_file():
            raise ChromeForTestingError(
                f"Chrome executable is missing from the archive: {binary_relative}"
            )
        if os.name != "nt":
            staged_binary.chmod(staged_binary.stat().st_mode | stat.S_IXUSR)

        metadata = {
            "schema_version": 1,
            "kind": CHROME_FOR_TESTING,
            "version": resolved_version,
            "platform": platform_name,
            "binary_path": binary_relative.as_posix(),
            "source_url": source_url,
            "archive_sha256": archive_sha256,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_write_json(staging_dir / METADATA_NAME, metadata)
        _replace_directory(staging_dir, install_dir)

    return load_chrome_for_testing(metadata_path)


def ensure_chrome_for_testing(
    version: str,
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
    expected_sha256: str | None = None,
) -> ChromeForTestingInstallation:
    platform_name = cft_platform or normalize_cft_platform()
    try:
        return resolve_chrome_for_testing(
            version,
            home=home,
            cft_platform=platform_name,
        )
    except ChromeForTestingError:
        return install_chrome_for_testing(
            version,
            home=home,
            cft_platform=platform_name,
            expected_sha256=expected_sha256,
        )


def list_chrome_for_testing(
    *,
    home: Path | str | None = None,
) -> list[ChromeForTestingInstallation]:
    home_path = (
        Path(home).expanduser()
        if home is not None
        else DEFAULT_CHROME_FOR_TESTING_HOME
    )
    installations: list[ChromeForTestingInstallation] = []
    if not home_path.is_dir():
        return installations
    for metadata_path in sorted(home_path.glob(f"*/*/{METADATA_NAME}")):
        try:
            _validate_install_location(home_path, metadata_path.parent)
            installations.append(load_chrome_for_testing(metadata_path))
        except ChromeForTestingError:
            continue
    return installations


def resolve_chrome_for_testing(
    version: str,
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
) -> ChromeForTestingInstallation:
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ChromeForTestingError(
            f"Chrome for Testing resolution requires an exact version: {version}"
        )
    platform_name = cft_platform or normalize_cft_platform()
    home_path = (
        Path(home).expanduser()
        if home is not None
        else DEFAULT_CHROME_FOR_TESTING_HOME
    )
    install_dir = home_path / version / platform_name
    _validate_install_location(home_path, install_dir)
    metadata_path = install_dir / METADATA_NAME
    if not metadata_path.is_file():
        raise ChromeForTestingError(
            f"Chrome for Testing is not installed: {version} ({platform_name})"
        )
    return load_chrome_for_testing(metadata_path)


def load_chrome_for_testing(metadata_path: Path | str) -> ChromeForTestingInstallation:
    metadata_file = Path(metadata_path)
    if metadata_file.is_symlink():
        raise ChromeForTestingError(
            f"Chrome for Testing metadata must not be a symlink: {metadata_file}"
        )
    try:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChromeForTestingError(
            f"Invalid Chrome for Testing metadata: {metadata_file}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ChromeForTestingError(
            f"Chrome for Testing metadata must be a JSON object: {metadata_file}"
        )

    required = {
        "kind",
        "version",
        "platform",
        "binary_path",
        "source_url",
        "archive_sha256",
        "installed_at",
    }
    missing = sorted(required - data.keys())
    if data.get("schema_version") != 1 or missing:
        raise ChromeForTestingError(
            f"Unsupported Chrome for Testing metadata: {metadata_file}; missing={missing}"
        )

    kind = str(data["kind"])
    version = str(data["version"])
    platform_name = str(data["platform"])
    source_url = str(data["source_url"])
    archive_sha256 = str(data["archive_sha256"])
    installed_at = str(data["installed_at"])
    if kind != CHROME_FOR_TESTING:
        raise ChromeForTestingError(
            f"Unexpected kind in Chrome for Testing metadata: {kind}"
        )
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ChromeForTestingError(f"Invalid Chrome version in metadata: {version}")
    if platform_name not in SUPPORTED_CFT_PLATFORMS:
        raise ChromeForTestingError(f"Unsupported platform in metadata: {platform_name}")
    _validate_download_url(source_url)
    _normalize_sha256(archive_sha256)
    if not installed_at:
        raise ChromeForTestingError(
            "Chrome for Testing metadata installed_at must not be empty"
        )

    root_dir = metadata_file.parent.resolve()
    expected_layout = (version, platform_name)
    actual_layout = (
        root_dir.parent.name,
        root_dir.name,
    )
    if actual_layout != expected_layout:
        raise ChromeForTestingError(
            f"Chrome for Testing metadata does not match its directory layout: {metadata_file}"
        )

    binary_relative = str(data["binary_path"])
    if binary_relative != _binary_relative_path(platform_name).as_posix():
        raise ChromeForTestingError(
            f"Unexpected browser executable path in metadata: {binary_relative}"
        )
    binary_path = (root_dir / binary_relative).resolve()
    if not binary_path.is_relative_to(root_dir):
        raise ChromeForTestingError(
            f"Chrome for Testing binary escapes its installation root: {binary_path}"
        )
    if not binary_path.is_file():
        raise ChromeForTestingError(
            f"Chrome for Testing binary is missing: {binary_path}"
        )

    return ChromeForTestingInstallation(
        kind=kind,
        version=version,
        platform=platform_name,
        root_dir=root_dir,
        binary_path=binary_path,
        source_url=source_url,
        archive_sha256=archive_sha256,
        installed_at=installed_at,
    )


def doctor_chrome_for_testing(
    runtime: ChromeForTestingInstallation,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    reported_version: str | None = None
    if not runtime.binary_path.is_file():
        errors.append("binary_missing")
    elif os.name != "nt" and not os.access(runtime.binary_path, os.X_OK):
        errors.append("binary_not_executable")

    if not errors and execute:
        try:
            result = subprocess.run(
                [str(runtime.binary_path), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=20,
            )
            reported_version = (result.stdout or result.stderr).strip()
            if runtime.version not in reported_version:
                errors.append("version_mismatch")
        except Exception as exc:  # noqa: BLE001 - doctor returns probe failures as data.
            errors.append(f"execution_failed:{exc}")

    return {
        **runtime.to_dict(),
        "status": "ready" if not errors else "unhealthy",
        "reported_version": reported_version,
        "errors": errors,
    }


def safe_extract_chrome_for_testing_zip(
    archive_path: Path | str,
    destination: Path | str,
) -> None:
    try:
        safe_extract_zip(
            archive_path,
            destination,
            label="Chrome for Testing",
        )
    except ManagedArtifactError as exc:
        raise ChromeForTestingError(str(exc)) from exc


def _binary_relative_path(cft_platform: str) -> Path:
    candidates = {
        "linux64": Path("chrome-linux64/chrome"),
        "mac-arm64": Path(
            "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        "mac-x64": Path(
            "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        "win64": Path("chrome-win64/chrome.exe"),
    }
    try:
        return candidates[cft_platform]
    except KeyError as exc:
        raise ChromeForTestingError(f"Unsupported Chrome for Testing platform: {cft_platform}") from exc


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != CFT_DOWNLOAD_HOST
        or not parsed.path.startswith(CFT_DOWNLOAD_PREFIX)
    ):
        raise ChromeForTestingError(
            "Chrome for Testing download must use the official Google storage prefix: "
            f"{url}"
        )


def _validate_resolved_identity(version: str, platform_name: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ChromeForTestingError(
            f"Chrome for Testing resolver returned an invalid version: {version}"
        )
    if platform_name not in SUPPORTED_CFT_PLATFORMS:
        raise ChromeForTestingError(
            "Chrome for Testing resolver returned an unsupported platform: "
            f"{platform_name}"
        )


def _validate_install_location(home: Path, install_dir: Path) -> None:
    home_resolved = home.expanduser().resolve()
    install_resolved = install_dir.expanduser().resolve()
    if not install_resolved.is_relative_to(home_resolved):
        raise ChromeForTestingError(
            f"Chrome for Testing installation escapes its managed home: {install_dir}"
        )


def remove_chrome_for_testing(
    version: str,
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
) -> ChromeForTestingInstallation:
    home_path = (
        Path(home).expanduser()
        if home is not None
        else DEFAULT_CHROME_FOR_TESTING_HOME
    )
    installation = resolve_chrome_for_testing(
        version,
        home=home_path,
        cft_platform=cft_platform,
    )
    try:
        remove_managed_directory(installation.root_dir, home=home_path)
    except ManagedArtifactError as exc:
        raise ChromeForTestingError(str(exc)) from exc
    version_dir = installation.root_dir.parent
    if version_dir.is_dir() and not any(version_dir.iterdir()):
        version_dir.rmdir()
    return installation


def garbage_collect_chrome_for_testing(
    *,
    home: Path | str | None = None,
    dry_run: bool = True,
    yes: bool = False,
    minimum_age_seconds: int = 24 * 60 * 60,
) -> dict[str, Any]:
    home_path = (
        Path(home).expanduser()
        if home is not None
        else DEFAULT_CHROME_FOR_TESTING_HOME
    )
    candidates = find_stale_directories(
        home_path,
        minimum_age_seconds=minimum_age_seconds,
    )
    if not dry_run and not yes:
        raise ChromeForTestingError(
            "Refusing to remove stale Chrome for Testing directories without yes=True"
        )
    removed: list[str] = []
    if not dry_run:
        for candidate in sorted(candidates, key=lambda path: len(path.parts), reverse=True):
            if not candidate.exists():
                continue
            try:
                remove_managed_directory(candidate, home=home_path)
            except ManagedArtifactError as exc:
                raise ChromeForTestingError(str(exc)) from exc
            removed.append(str(candidate))
    return {
        "kind": CHROME_FOR_TESTING,
        "home": str(home_path),
        "dry_run": dry_run,
        "candidates": [str(path) for path in candidates],
        "removed": removed,
    }


def _normalize_sha256(value: str | None) -> str | None:
    try:
        return normalize_sha256(value)
    except ManagedArtifactError as exc:
        raise ChromeForTestingError(str(exc)) from exc


def _sha256_file(path: Path) -> str:
    return sha256_file(path)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data)


def _replace_directory(staging_dir: Path, install_dir: Path) -> None:
    replace_directory(staging_dir, install_dir)
