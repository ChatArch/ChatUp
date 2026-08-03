from __future__ import annotations

import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

CHROME_FOR_TESTING = "chrome-for-testing"
CFT_CHANNELS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
CFT_VERSIONS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "known-good-versions-with-downloads.json"
)
DEFAULT_BROWSER_HOME = Path.home() / ".chatarch" / "chrome"
METADATA_NAME = "runtime.json"
SUPPORTED_CFT_PLATFORMS = ("linux64", "mac-arm64", "mac-x64", "win64")
MAX_ARCHIVE_FILES = 100_000
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
CFT_DOWNLOAD_HOST = "storage.googleapis.com"
CFT_DOWNLOAD_PREFIX = "/chrome-for-testing-public/"


class BrowserRuntimeError(RuntimeError):
    """Raised when a managed browser runtime cannot be resolved safely."""


@dataclass(frozen=True)
class BrowserRuntime:
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

    raise BrowserRuntimeError(
        f"Chrome for Testing does not provide a supported build for "
        f"system={system_name!r}, machine={machine_name!r}"
    )


def fetch_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp/browser-runtime"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:
        raise BrowserRuntimeError(f"Failed to fetch browser manifest: {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BrowserRuntimeError(f"Browser manifest is not an object: {url}")
    return payload


def download_file(url: str, destination: Path, *, timeout: float = 120.0) -> None:
    _validate_download_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp/browser-runtime"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise BrowserRuntimeError("Browser archive exceeds the 1 GiB download limit")
            with destination.open("wb") as output:
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_ARCHIVE_BYTES:
                        raise BrowserRuntimeError("Browser archive exceeds the 1 GiB download limit")
                    output.write(chunk)
    except Exception as exc:
        raise BrowserRuntimeError(f"Failed to download browser archive: {url}: {exc}") from exc


def resolve_chrome_for_testing_download(
    version: str = "stable",
    *,
    cft_platform: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
) -> tuple[str, str, str]:
    requested = version.strip()
    if not requested:
        raise BrowserRuntimeError("Browser version must not be empty")
    platform_name = cft_platform or normalize_cft_platform()
    if platform_name not in SUPPORTED_CFT_PLATFORMS:
        raise BrowserRuntimeError(f"Unsupported Chrome for Testing platform: {platform_name}")

    channel_names = {name.lower(): name for name in ("Stable", "Beta", "Dev", "Canary")}
    if requested.lower() in channel_names:
        data = fetcher(CFT_CHANNELS_URL)
        entry = data.get("channels", {}).get(channel_names[requested.lower()])
    else:
        data = fetcher(CFT_VERSIONS_URL)
        entry = next(
            (item for item in data.get("versions", []) if item.get("version") == requested),
            None,
        )

    if not isinstance(entry, dict) or not entry.get("version"):
        raise BrowserRuntimeError(f"Chrome for Testing version not found: {requested}")

    downloads = entry.get("downloads", {}).get("chrome", [])
    artifact = next(
        (item for item in downloads if item.get("platform") == platform_name),
        None,
    )
    if not isinstance(artifact, dict) or not artifact.get("url"):
        raise BrowserRuntimeError(
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
) -> BrowserRuntime:
    resolved_version, platform_name, source_url = resolver(
        version,
        cft_platform=cft_platform,
    )
    _validate_download_url(source_url)
    browser_home = Path(home).expanduser() if home is not None else DEFAULT_BROWSER_HOME
    install_dir = browser_home / CHROME_FOR_TESTING / resolved_version / platform_name
    metadata_path = install_dir / METADATA_NAME
    normalized_expected = _normalize_sha256(expected_sha256)

    if metadata_path.is_file() and not force:
        runtime = load_browser_runtime(metadata_path)
        if normalized_expected and runtime.archive_sha256 != normalized_expected:
            raise BrowserRuntimeError(
                "Installed browser SHA-256 does not match the expected archive digest"
            )
        return runtime
    if install_dir.exists() and not force:
        raise BrowserRuntimeError(
            f"Browser runtime directory exists without valid metadata: {install_dir}; use force to replace it"
        )

    install_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".{platform_name}-install-",
        dir=install_dir.parent,
    ) as temporary:
        temporary_dir = Path(temporary)
        archive_path = temporary_dir / "browser.zip"
        staging_dir = temporary_dir / "runtime"
        downloader(source_url, archive_path)

        archive_sha256 = _sha256_file(archive_path)
        if normalized_expected and archive_sha256 != normalized_expected:
            raise BrowserRuntimeError(
                f"Browser archive SHA-256 mismatch: expected {normalized_expected}, got {archive_sha256}"
            )

        safe_extract_zip(archive_path, staging_dir)
        binary_relative = _binary_relative_path(platform_name)
        staged_binary = staging_dir / binary_relative
        if not staged_binary.is_file():
            raise BrowserRuntimeError(
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

    return load_browser_runtime(metadata_path)


def ensure_chrome_for_testing(
    version: str,
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
    expected_sha256: str | None = None,
) -> BrowserRuntime:
    platform_name = cft_platform or normalize_cft_platform()
    try:
        return resolve_browser_runtime(
            f"{CHROME_FOR_TESTING}@{version}",
            home=home,
            cft_platform=platform_name,
        )
    except BrowserRuntimeError:
        return install_chrome_for_testing(
            version,
            home=home,
            cft_platform=platform_name,
            expected_sha256=expected_sha256,
        )


def list_browser_runtimes(*, home: Path | str | None = None) -> list[BrowserRuntime]:
    browser_home = Path(home).expanduser() if home is not None else DEFAULT_BROWSER_HOME
    runtimes: list[BrowserRuntime] = []
    if not browser_home.is_dir():
        return runtimes
    for metadata_path in sorted(browser_home.glob(f"*/*/*/{METADATA_NAME}")):
        try:
            runtimes.append(load_browser_runtime(metadata_path))
        except BrowserRuntimeError:
            continue
    return runtimes


def resolve_browser_runtime(
    ref: str,
    *,
    home: Path | str | None = None,
    cft_platform: str | None = None,
) -> BrowserRuntime:
    kind, separator, version = ref.partition("@")
    if not separator or not kind or not version:
        raise BrowserRuntimeError(
            "Browser reference must use <kind>@<version>, for example chrome-for-testing@145.0.7632.6"
        )
    if kind in {"chrome", "cft"}:
        kind = CHROME_FOR_TESTING
    if kind != CHROME_FOR_TESTING:
        raise BrowserRuntimeError(f"Unsupported browser runtime kind: {kind}")

    platform_name = cft_platform or normalize_cft_platform()
    browser_home = Path(home).expanduser() if home is not None else DEFAULT_BROWSER_HOME
    metadata_path = browser_home / kind / version / platform_name / METADATA_NAME
    if not metadata_path.is_file():
        raise BrowserRuntimeError(f"Browser runtime is not installed: {kind}@{version} ({platform_name})")
    return load_browser_runtime(metadata_path)


def load_browser_runtime(metadata_path: Path | str) -> BrowserRuntime:
    metadata_file = Path(metadata_path)
    try:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BrowserRuntimeError(f"Invalid browser runtime metadata: {metadata_file}: {exc}") from exc

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
        raise BrowserRuntimeError(
            f"Unsupported browser runtime metadata: {metadata_file}; missing={missing}"
        )

    kind = str(data["kind"])
    version = str(data["version"])
    platform_name = str(data["platform"])
    source_url = str(data["source_url"])
    archive_sha256 = str(data["archive_sha256"])
    installed_at = str(data["installed_at"])
    if kind != CHROME_FOR_TESTING:
        raise BrowserRuntimeError(f"Unsupported browser kind in metadata: {kind}")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise BrowserRuntimeError(f"Invalid Chrome version in metadata: {version}")
    if platform_name not in SUPPORTED_CFT_PLATFORMS:
        raise BrowserRuntimeError(f"Unsupported platform in metadata: {platform_name}")
    _validate_download_url(source_url)
    _normalize_sha256(archive_sha256)
    if not installed_at:
        raise BrowserRuntimeError("Browser metadata installed_at must not be empty")

    root_dir = metadata_file.parent.resolve()
    expected_layout = (kind, version, platform_name)
    actual_layout = (
        root_dir.parent.parent.name,
        root_dir.parent.name,
        root_dir.name,
    )
    if actual_layout != expected_layout:
        raise BrowserRuntimeError(
            f"Browser metadata does not match its directory layout: {metadata_file}"
        )

    binary_relative = str(data["binary_path"])
    if binary_relative != _binary_relative_path(platform_name).as_posix():
        raise BrowserRuntimeError(
            f"Unexpected browser executable path in metadata: {binary_relative}"
        )
    binary_path = (root_dir / binary_relative).resolve()
    if not binary_path.is_relative_to(root_dir):
        raise BrowserRuntimeError(f"Browser binary escapes runtime root: {binary_path}")
    if not binary_path.is_file():
        raise BrowserRuntimeError(f"Browser binary is missing: {binary_path}")

    return BrowserRuntime(
        kind=kind,
        version=version,
        platform=platform_name,
        root_dir=root_dir,
        binary_path=binary_path,
        source_url=source_url,
        archive_sha256=archive_sha256,
        installed_at=installed_at,
    )


def doctor_browser_runtime(
    runtime: BrowserRuntime,
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
        except Exception as exc:
            errors.append(f"execution_failed:{exc}")

    return {
        **runtime.to_dict(),
        "status": "ready" if not errors else "unhealthy",
        "reported_version": reported_version,
        "errors": errors,
    }


def safe_extract_zip(archive_path: Path | str, destination: Path | str) -> None:
    archive = Path(archive_path)
    target_root = Path(destination)
    target_root.mkdir(parents=True, exist_ok=True)
    root_resolved = target_root.resolve()

    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_ARCHIVE_FILES:
                raise BrowserRuntimeError("Browser archive contains too many files")
            if sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES:
                raise BrowserRuntimeError("Browser archive is too large after extraction")

            for member in members:
                normalized_name = member.filename.replace("\\", "/")
                relative = PurePosixPath(normalized_name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise BrowserRuntimeError(
                        f"Unsafe path in browser archive: {member.filename}"
                    )
                mode = (member.external_attr >> 16) & 0xFFFF

                target = (target_root / Path(*relative.parts)).resolve()
                if not target.is_relative_to(root_resolved):
                    raise BrowserRuntimeError(
                        f"Archive member escapes extraction root: {member.filename}"
                    )
                if stat.S_ISLNK(mode):
                    try:
                        link_value = bundle.read(member).decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise BrowserRuntimeError(
                            f"Invalid symlink target in browser archive: {member.filename}"
                        ) from exc
                    link_path = Path(link_value)
                    if link_path.is_absolute():
                        raise BrowserRuntimeError(
                            f"Absolute symlink is not allowed in browser archive: {member.filename}"
                        )
                    resolved_link = (target.parent / link_path).resolve()
                    if not resolved_link.is_relative_to(root_resolved):
                        raise BrowserRuntimeError(
                            f"Symlink escapes browser archive root: {member.filename}"
                        )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(link_value)
                    continue
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                permissions = mode & 0o777
                if permissions and os.name != "nt":
                    target.chmod(permissions)
    except zipfile.BadZipFile as exc:
        raise BrowserRuntimeError(f"Invalid browser archive: {archive}: {exc}") from exc


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
        raise BrowserRuntimeError(f"Unsupported Chrome for Testing platform: {cft_platform}") from exc


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != CFT_DOWNLOAD_HOST
        or not parsed.path.startswith(CFT_DOWNLOAD_PREFIX)
    ):
        raise BrowserRuntimeError(
            "Chrome for Testing download must use the official Google storage prefix: "
            f"{url}"
        )


def _normalize_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise BrowserRuntimeError("Expected SHA-256 must contain exactly 64 hexadecimal characters")
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _replace_directory(staging_dir: Path, install_dir: Path) -> None:
    backup_dir = install_dir.with_name(f".{install_dir.name}.backup-{uuid.uuid4().hex}")
    had_existing = install_dir.exists()
    if had_existing:
        install_dir.rename(backup_dir)
    try:
        staging_dir.rename(install_dir)
    except Exception:
        if had_existing and backup_dir.exists() and not install_dir.exists():
            backup_dir.rename(install_dir)
        raise
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
