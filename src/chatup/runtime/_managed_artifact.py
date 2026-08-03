from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ARCHIVE_FILES = 100_000
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_GC_MINIMUM_AGE_SECONDS = 24 * 60 * 60


class ManagedArtifactError(RuntimeError):
    """Raised when a managed artifact filesystem operation is unsafe."""


def safe_extract_zip(
    archive_path: Path | str,
    destination: Path | str,
    *,
    label: str,
) -> None:
    archive = Path(archive_path)
    target_root = Path(destination)
    target_root.mkdir(parents=True, exist_ok=True)
    root_resolved = target_root.resolve()

    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_ARCHIVE_FILES:
                raise ManagedArtifactError(f"{label} archive contains too many files")
            if sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES:
                raise ManagedArtifactError(
                    f"{label} archive is too large after extraction"
                )

            for member in members:
                relative = PurePosixPath(member.filename.replace("\\", "/"))
                if relative.is_absolute() or ".." in relative.parts:
                    raise ManagedArtifactError(
                        f"Unsafe path in {label} archive: {member.filename}"
                    )
                mode = (member.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                allowed_types = {0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}
                if file_type not in allowed_types:
                    raise ManagedArtifactError(
                        f"Unsupported file type in {label} archive: {member.filename}"
                    )

                target = (target_root / Path(*relative.parts)).resolve()
                if not target.is_relative_to(root_resolved):
                    raise ManagedArtifactError(
                        f"Archive member escapes {label} extraction root: {member.filename}"
                    )
                if stat.S_ISLNK(mode):
                    try:
                        link_value = bundle.read(member).decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ManagedArtifactError(
                            f"Invalid symlink target in {label} archive: {member.filename}"
                        ) from exc
                    link_path = Path(link_value)
                    if link_path.is_absolute():
                        raise ManagedArtifactError(
                            f"Absolute symlink is not allowed in {label} archive: {member.filename}"
                        )
                    resolved_link = (target.parent / link_path).resolve()
                    if not resolved_link.is_relative_to(root_resolved):
                        raise ManagedArtifactError(
                            f"Symlink escapes {label} archive root: {member.filename}"
                        )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(link_value)
                    continue
                if member.is_dir() or stat.S_ISDIR(mode):
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                permissions = mode & 0o777
                if permissions and os.name != "nt":
                    target.chmod(permissions)
    except ManagedArtifactError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ManagedArtifactError(f"Invalid {label} archive: {archive}: {exc}") from exc


def normalize_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ManagedArtifactError(
            "Expected SHA-256 must contain exactly 64 hexadecimal characters"
        )
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def replace_directory(staging_dir: Path, install_dir: Path) -> None:
    backup_dir = install_dir.with_name(
        f".{install_dir.name}.backup-{uuid.uuid4().hex}"
    )
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


def remove_managed_directory(path: Path, *, home: Path) -> None:
    home_resolved = home.expanduser().resolve()
    path_resolved = path.resolve()
    if path_resolved == home_resolved or not path_resolved.is_relative_to(home_resolved):
        raise ManagedArtifactError(
            f"Refusing to remove a path outside the managed home: {path_resolved}"
        )
    if path.is_symlink():
        raise ManagedArtifactError(
            f"Refusing to remove a symlink as an installation root: {path}"
        )
    shutil.rmtree(path_resolved)


def find_stale_directories(
    home: Path | str,
    *,
    minimum_age_seconds: int = DEFAULT_GC_MINIMUM_AGE_SECONDS,
    now: float | None = None,
) -> list[Path]:
    home_path = Path(home).expanduser()
    if not home_path.is_dir():
        return []
    cutoff = (time.time() if now is None else now) - minimum_age_seconds
    candidates: list[Path] = []
    for path in home_path.rglob(".*"):
        if not path.is_dir() or path.is_symlink():
            continue
        name = path.name
        if ".backup-" not in name and "-install-" not in name:
            continue
        if path.stat().st_mtime <= cutoff:
            candidates.append(path)
    return sorted(candidates)
