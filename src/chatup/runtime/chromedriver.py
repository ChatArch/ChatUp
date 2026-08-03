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

CHROMEDRIVER = "chromedriver"
CHROMEDRIVER_CHANNELS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
CHROMEDRIVER_VERSIONS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "known-good-versions-with-downloads.json"
)
CHROMEDRIVER_PATCH_BUILDS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "latest-patch-versions-per-build-with-downloads.json"
)
CHROMEDRIVER_MILESTONES_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "latest-versions-per-milestone-with-downloads.json"
)
DEFAULT_CHROMEDRIVER_HOME = Path.home() / ".chatarch" / CHROMEDRIVER
METADATA_NAME = "installation.json"
SUPPORTED_CHROMEDRIVER_PLATFORMS = (
    "linux64",
    "mac-arm64",
    "mac-x64",
    "win64",
)
CHROMEDRIVER_DOWNLOAD_HOST = "storage.googleapis.com"
CHROMEDRIVER_DOWNLOAD_PREFIX = "/chrome-for-testing-public/"


class ChromeDriverError(RuntimeError):
    """Raised when ChromeDriver cannot be managed safely."""


@dataclass(frozen=True)
class ChromeDriverInstallation:
    kind: str
    version: str
    platform: str
    root_dir: Path
    binary_path: Path
    source_url: str
    archive_sha256: str
    installed_at: str
    matched_browser_version: str | None = None

    @property
    def ref(self) -> str:
        return f"{self.kind}@{self.version}"

    def to_dict(self) -> dict[str, str | None]:
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
            "matched_browser_version": self.matched_browser_version,
        }


def normalize_chromedriver_platform(
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

    raise ChromeDriverError(
        "ChromeDriver does not provide a supported build for "
        f"system={system_name!r}, machine={machine_name!r}"
    )


def fetch_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatUp/chromedriver"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:
        raise ChromeDriverError(
            f"Failed to fetch ChromeDriver manifest: {url}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ChromeDriverError(f"ChromeDriver manifest is not an object: {url}")
    return payload


def download_file(url: str, destination: Path, *, timeout: float = 120.0) -> None:
    _validate_download_url(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatUp/chromedriver"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise ChromeDriverError(
                    "ChromeDriver archive exceeds the 1 GiB download limit"
                )
            with destination.open("wb") as output:
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_ARCHIVE_BYTES:
                        raise ChromeDriverError(
                            "ChromeDriver archive exceeds the 1 GiB download limit"
                        )
                    output.write(chunk)
    except Exception as exc:
        raise ChromeDriverError(
            f"Failed to download ChromeDriver archive: {url}: {exc}"
        ) from exc


def _resolve_driver_artifact(
    entry: Any,
    *,
    platform_name: str,
    request_label: str,
) -> tuple[str, str, str]:
    if not isinstance(entry, dict) or not entry.get("version"):
        raise ChromeDriverError(f"ChromeDriver version not found: {request_label}")

    download_groups = entry.get("downloads")
    downloads = (
        download_groups.get(CHROMEDRIVER, [])
        if isinstance(download_groups, dict)
        else []
    )
    artifact = (
        next(
            (
                item
                for item in downloads
                if isinstance(item, dict) and item.get("platform") == platform_name
            ),
            None,
        )
        if isinstance(downloads, list)
        else None
    )
    if not isinstance(artifact, dict) or not artifact.get("url"):
        raise ChromeDriverError(
            f"ChromeDriver {entry['version']} has no {platform_name} download"
        )

    url = str(artifact["url"])
    _validate_download_url(url)
    return str(entry["version"]), platform_name, url


def resolve_chromedriver_download(
    version: str = "stable",
    *,
    driver_platform: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
) -> tuple[str, str, str]:
    requested = version.strip()
    if not requested:
        raise ChromeDriverError("ChromeDriver version must not be empty")
    platform_name = driver_platform or normalize_chromedriver_platform()
    if platform_name not in SUPPORTED_CHROMEDRIVER_PLATFORMS:
        raise ChromeDriverError(f"Unsupported ChromeDriver platform: {platform_name}")

    channel_names = {
        name.lower(): name for name in ("Stable", "Beta", "Dev", "Canary")
    }
    if requested.lower() in channel_names:
        data = fetcher(CHROMEDRIVER_CHANNELS_URL)
        channels = data.get("channels")
        entry = (
            channels.get(channel_names[requested.lower()])
            if isinstance(channels, dict)
            else None
        )
    else:
        data = fetcher(CHROMEDRIVER_VERSIONS_URL)
        versions = data.get("versions")
        entry = (
            next(
                (
                    item
                    for item in versions
                    if isinstance(item, dict) and item.get("version") == requested
                ),
                None,
            )
            if isinstance(versions, list)
            else None
        )

    return _resolve_driver_artifact(
        entry,
        platform_name=platform_name,
        request_label=requested,
    )


def resolve_chromedriver_for_browser_version(
    browser_version: str,
    *,
    driver_platform: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
) -> tuple[str, str, str]:
    requested = browser_version.strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", requested):
        raise ChromeDriverError(
            "Browser version must contain four numeric components"
        )
    platform_name = driver_platform or normalize_chromedriver_platform()
    if platform_name not in SUPPORTED_CHROMEDRIVER_PLATFORMS:
        raise ChromeDriverError(f"Unsupported ChromeDriver platform: {platform_name}")

    major, minor, build, _patch = requested.split(".")
    build_key = f"{major}.{minor}.{build}"
    patch_data = fetcher(CHROMEDRIVER_PATCH_BUILDS_URL)
    builds = patch_data.get("builds")
    entry = builds.get(build_key) if isinstance(builds, dict) else None

    if not isinstance(entry, dict):
        milestone_data = fetcher(CHROMEDRIVER_MILESTONES_URL)
        milestones = milestone_data.get("milestones")
        entry = milestones.get(major) if isinstance(milestones, dict) else None

    if not isinstance(entry, dict):
        raise ChromeDriverError(
            f"No ChromeDriver match found for browser version: {requested}"
        )
    return _resolve_driver_artifact(
        entry,
        platform_name=platform_name,
        request_label=requested,
    )


def read_browser_version(
    browser_path: Path | str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    path = Path(browser_path).expanduser()
    if not path.is_file():
        raise ChromeDriverError(f"Browser binary is not a file: {path}")
    try:
        result = runner(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
    except Exception as exc:
        raise ChromeDriverError(
            f"Failed to read browser version from {path}: {exc}"
        ) from exc
    output = (result.stdout or result.stderr).strip()
    match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", output)
    if match is None:
        raise ChromeDriverError(
            f"Browser did not report a four-component version: {output!r}"
        )
    return match.group(1)


def install_chromedriver(
    version: str | None = None,
    *,
    match_browser: Path | str | None = None,
    match_cft_version: str | None = None,
    home: Path | str | None = None,
    driver_platform: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
    resolver: Callable[..., tuple[str, str, str]] = resolve_chromedriver_download,
    browser_match_resolver: Callable[..., tuple[str, str, str]] = (
        resolve_chromedriver_for_browser_version
    ),
    downloader: Callable[[str, Path], None] = download_file,
    browser_version_reader: Callable[[Path | str], str] = read_browser_version,
) -> ChromeDriverInstallation:
    selected = [
        value
        for value in (version, match_browser, match_cft_version)
        if value is not None and str(value).strip()
    ]
    if len(selected) > 1:
        raise ChromeDriverError(
            "Choose only one of version, match_browser, or match_cft_version"
        )

    matched_browser_version: str | None = None
    if match_browser is not None:
        matched_browser_version = browser_version_reader(match_browser)
        resolved_version, platform_name, source_url = browser_match_resolver(
            matched_browser_version,
            driver_platform=driver_platform,
        )
    elif match_cft_version is not None:
        requested_version = match_cft_version.strip()
        matched_browser_version = requested_version
        resolved_version, platform_name, source_url = resolver(
            requested_version,
            driver_platform=driver_platform,
        )
    else:
        requested_version = (version or "stable").strip()
        resolved_version, platform_name, source_url = resolver(
            requested_version,
            driver_platform=driver_platform,
        )
    _validate_download_url(source_url)
    home_path = (
        Path(home).expanduser() if home is not None else DEFAULT_CHROMEDRIVER_HOME
    )
    install_dir = home_path / resolved_version / platform_name
    metadata_path = install_dir / METADATA_NAME
    normalized_expected = _normalize_sha256(expected_sha256)

    if install_dir.is_symlink():
        raise ChromeDriverError(
            f"Refusing to use a symlink as a ChromeDriver installation root: {install_dir}"
        )
    if metadata_path.is_file() and not force:
        installation = load_chromedriver(metadata_path)
        if normalized_expected and installation.archive_sha256 != normalized_expected:
            raise ChromeDriverError(
                "Installed ChromeDriver SHA-256 does not match the expected archive digest"
            )
        return installation
    if install_dir.exists() and not force:
        raise ChromeDriverError(
            f"ChromeDriver directory exists without valid metadata: {install_dir}; use force to replace it"
        )

    install_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{platform_name}-install-",
        dir=install_dir.parent,
    ) as temporary:
        temporary_dir = Path(temporary)
        archive_path = temporary_dir / "chromedriver.zip"
        staging_dir = temporary_dir / "installation"
        downloader(source_url, archive_path)

        archive_sha256 = sha256_file(archive_path)
        if normalized_expected and archive_sha256 != normalized_expected:
            raise ChromeDriverError(
                "ChromeDriver archive SHA-256 mismatch: "
                f"expected {normalized_expected}, got {archive_sha256}"
            )
        safe_extract_chromedriver_zip(archive_path, staging_dir)
        binary_relative = _binary_relative_path(platform_name)
        staged_binary = staging_dir / binary_relative
        if not staged_binary.is_file():
            raise ChromeDriverError(
                f"ChromeDriver executable is missing from the archive: {binary_relative}"
            )
        if os.name != "nt":
            staged_binary.chmod(staged_binary.stat().st_mode | stat.S_IXUSR)

        metadata = {
            "schema_version": 1,
            "kind": CHROMEDRIVER,
            "version": resolved_version,
            "platform": platform_name,
            "binary_path": binary_relative.as_posix(),
            "source_url": source_url,
            "archive_sha256": archive_sha256,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "matched_browser_version": matched_browser_version,
        }
        atomic_write_json(staging_dir / METADATA_NAME, metadata)
        replace_directory(staging_dir, install_dir)

    return load_chromedriver(metadata_path)


def ensure_chromedriver(
    version: str,
    *,
    home: Path | str | None = None,
    driver_platform: str | None = None,
    expected_sha256: str | None = None,
) -> ChromeDriverInstallation:
    platform_name = driver_platform or normalize_chromedriver_platform()
    try:
        return resolve_chromedriver(
            version,
            home=home,
            driver_platform=platform_name,
        )
    except ChromeDriverError:
        return install_chromedriver(
            version,
            home=home,
            driver_platform=platform_name,
            expected_sha256=expected_sha256,
        )


def list_chromedrivers(
    *,
    home: Path | str | None = None,
) -> list[ChromeDriverInstallation]:
    home_path = (
        Path(home).expanduser() if home is not None else DEFAULT_CHROMEDRIVER_HOME
    )
    installations: list[ChromeDriverInstallation] = []
    if not home_path.is_dir():
        return installations
    for metadata_path in sorted(home_path.glob(f"*/*/{METADATA_NAME}")):
        try:
            installations.append(load_chromedriver(metadata_path))
        except ChromeDriverError:
            continue
    return installations


def resolve_chromedriver(
    version: str,
    *,
    home: Path | str | None = None,
    driver_platform: str | None = None,
) -> ChromeDriverInstallation:
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ChromeDriverError(
            f"ChromeDriver resolution requires an exact version: {version}"
        )
    platform_name = driver_platform or normalize_chromedriver_platform()
    home_path = (
        Path(home).expanduser() if home is not None else DEFAULT_CHROMEDRIVER_HOME
    )
    metadata_path = home_path / version / platform_name / METADATA_NAME
    if not metadata_path.is_file():
        raise ChromeDriverError(
            f"ChromeDriver is not installed: {version} ({platform_name})"
        )
    return load_chromedriver(metadata_path)


def load_chromedriver(metadata_path: Path | str) -> ChromeDriverInstallation:
    metadata_file = Path(metadata_path)
    if metadata_file.is_symlink():
        raise ChromeDriverError(
            f"ChromeDriver metadata must not be a symlink: {metadata_file}"
        )
    try:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChromeDriverError(
            f"Invalid ChromeDriver metadata: {metadata_file}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ChromeDriverError(
            f"ChromeDriver metadata must be a JSON object: {metadata_file}"
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
        raise ChromeDriverError(
            f"Unsupported ChromeDriver metadata: {metadata_file}; missing={missing}"
        )

    kind = str(data["kind"])
    version = str(data["version"])
    platform_name = str(data["platform"])
    source_url = str(data["source_url"])
    archive_sha256 = str(data["archive_sha256"])
    installed_at = str(data["installed_at"])
    matched_browser_version = data.get("matched_browser_version")
    if matched_browser_version is not None:
        matched_browser_version = str(matched_browser_version)

    if kind != CHROMEDRIVER:
        raise ChromeDriverError(f"Unexpected kind in ChromeDriver metadata: {kind}")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ChromeDriverError(f"Invalid ChromeDriver version in metadata: {version}")
    if matched_browser_version is not None and not re.fullmatch(
        r"\d+\.\d+\.\d+\.\d+", matched_browser_version
    ):
        raise ChromeDriverError(
            f"Invalid matched browser version in metadata: {matched_browser_version}"
        )
    if platform_name not in SUPPORTED_CHROMEDRIVER_PLATFORMS:
        raise ChromeDriverError(f"Unsupported platform in metadata: {platform_name}")
    _validate_download_url(source_url)
    _normalize_sha256(archive_sha256)
    if not installed_at:
        raise ChromeDriverError("ChromeDriver metadata installed_at must not be empty")

    root_dir = metadata_file.parent.resolve()
    if (root_dir.parent.name, root_dir.name) != (version, platform_name):
        raise ChromeDriverError(
            f"ChromeDriver metadata does not match its directory layout: {metadata_file}"
        )
    binary_relative = str(data["binary_path"])
    if binary_relative != _binary_relative_path(platform_name).as_posix():
        raise ChromeDriverError(
            f"Unexpected ChromeDriver executable path in metadata: {binary_relative}"
        )
    binary_path = (root_dir / binary_relative).resolve()
    if not binary_path.is_relative_to(root_dir):
        raise ChromeDriverError(
            f"ChromeDriver binary escapes its installation root: {binary_path}"
        )
    if not binary_path.is_file():
        raise ChromeDriverError(f"ChromeDriver binary is missing: {binary_path}")

    return ChromeDriverInstallation(
        kind=kind,
        version=version,
        platform=platform_name,
        root_dir=root_dir,
        binary_path=binary_path,
        source_url=source_url,
        archive_sha256=archive_sha256,
        installed_at=installed_at,
        matched_browser_version=matched_browser_version,
    )


def doctor_chromedriver(
    installation: ChromeDriverInstallation,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    reported_version: str | None = None
    if not installation.binary_path.is_file():
        errors.append("binary_missing")
    elif os.name != "nt" and not os.access(installation.binary_path, os.X_OK):
        errors.append("binary_not_executable")

    if not errors and execute:
        try:
            result = subprocess.run(
                [str(installation.binary_path), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=20,
            )
            reported_version = (result.stdout or result.stderr).strip()
            if installation.version not in reported_version:
                errors.append("version_mismatch")
        except Exception as exc:  # noqa: BLE001 - doctor returns probe failures as data.
            errors.append(f"execution_failed:{exc}")

    return {
        **installation.to_dict(),
        "status": "ready" if not errors else "unhealthy",
        "reported_version": reported_version,
        "errors": errors,
    }


def remove_chromedriver(
    version: str,
    *,
    home: Path | str | None = None,
    driver_platform: str | None = None,
) -> ChromeDriverInstallation:
    home_path = (
        Path(home).expanduser() if home is not None else DEFAULT_CHROMEDRIVER_HOME
    )
    installation = resolve_chromedriver(
        version,
        home=home_path,
        driver_platform=driver_platform,
    )
    try:
        remove_managed_directory(installation.root_dir, home=home_path)
    except ManagedArtifactError as exc:
        raise ChromeDriverError(str(exc)) from exc
    version_dir = installation.root_dir.parent
    if version_dir.is_dir() and not any(version_dir.iterdir()):
        version_dir.rmdir()
    return installation


def garbage_collect_chromedriver(
    *,
    home: Path | str | None = None,
    dry_run: bool = True,
    yes: bool = False,
    minimum_age_seconds: int = 24 * 60 * 60,
) -> dict[str, Any]:
    home_path = (
        Path(home).expanduser() if home is not None else DEFAULT_CHROMEDRIVER_HOME
    )
    candidates = find_stale_directories(
        home_path,
        minimum_age_seconds=minimum_age_seconds,
    )
    if not dry_run and not yes:
        raise ChromeDriverError(
            "Refusing to remove stale ChromeDriver directories without yes=True"
        )
    removed: list[str] = []
    if not dry_run:
        for candidate in sorted(
            candidates,
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            if not candidate.exists():
                continue
            try:
                remove_managed_directory(candidate, home=home_path)
            except ManagedArtifactError as exc:
                raise ChromeDriverError(str(exc)) from exc
            removed.append(str(candidate))
    return {
        "kind": CHROMEDRIVER,
        "home": str(home_path),
        "dry_run": dry_run,
        "candidates": [str(path) for path in candidates],
        "removed": removed,
    }


def safe_extract_chromedriver_zip(
    archive_path: Path | str,
    destination: Path | str,
) -> None:
    try:
        safe_extract_zip(archive_path, destination, label="ChromeDriver")
    except ManagedArtifactError as exc:
        raise ChromeDriverError(str(exc)) from exc


def _binary_relative_path(driver_platform: str) -> Path:
    candidates = {
        "linux64": Path("chromedriver-linux64/chromedriver"),
        "mac-arm64": Path("chromedriver-mac-arm64/chromedriver"),
        "mac-x64": Path("chromedriver-mac-x64/chromedriver"),
        "win64": Path("chromedriver-win64/chromedriver.exe"),
    }
    try:
        return candidates[driver_platform]
    except KeyError as exc:
        raise ChromeDriverError(
            f"Unsupported ChromeDriver platform: {driver_platform}"
        ) from exc


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != CHROMEDRIVER_DOWNLOAD_HOST
        or not parsed.path.startswith(CHROMEDRIVER_DOWNLOAD_PREFIX)
    ):
        raise ChromeDriverError(
            "ChromeDriver download must use the official Google storage prefix: "
            f"{url}"
        )


def _normalize_sha256(value: str | None) -> str | None:
    try:
        return normalize_sha256(value)
    except ManagedArtifactError as exc:
        raise ChromeDriverError(str(exc)) from exc
