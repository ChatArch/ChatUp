"""Install the maintained ChatArch Glance release into a portable runtime."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import tempfile
import urllib.request

import click
from chatenv import get_paths
from chatglance.portable import initialize, install_verified_binary, runtime_home


DEFAULT_GLANCE_REPO = "ChatArch/glance"
DEFAULT_GLANCE_VERSION = "latest"
TAG_PATTERN = re.compile(r"chatarch-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SOURCE_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class GlanceInstallation:
    status: str
    tag: str
    version: str | None
    binary: Path
    config: Path
    start_command: tuple[str, ...]


def normalize_release_tag(value: str) -> str:
    tag = str(value).strip()
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Glance version must be an exact chatarch-vMAJOR.MINOR.PATCH tag")
    return tag


def _require_supported_platform() -> None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system != "linux" or machine not in {"x86_64", "amd64"}:
        raise ValueError("Maintained ChatArch/glance releases currently support Linux amd64 only")


def resolve_latest_release_tag(repo: str = DEFAULT_GLANCE_REPO) -> str:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = payload.get("tag_name")
    if not isinstance(tag, str):
        raise ValueError(f"Latest {repo} release did not provide a tag")
    return normalize_release_tag(tag)


def resolve_requested_tag(version: str, repo: str = DEFAULT_GLANCE_REPO) -> str:
    value = str(version or DEFAULT_GLANCE_VERSION).strip()
    return resolve_latest_release_tag(repo) if value == DEFAULT_GLANCE_VERSION else normalize_release_tag(value)


def release_asset_name(tag: str) -> str:
    return f"glance-{normalize_release_tag(tag)}-linux-amd64.tar.gz"


def release_asset_url(repo: str, tag: str, name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{name}"


def download_release_asset(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as output:
        status = getattr(response, "status", 200)
        if status != 200:
            raise ValueError(f"Glance release download failed with HTTP {status}")
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksums(path: Path, expected_names: set[str]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._+-]+)", line)
        if not match or match.group(2) in checksums:
            raise ValueError("Invalid SHA256SUMS manifest")
        checksums[match.group(2)] = match.group(1)
    if set(checksums) != expected_names:
        raise ValueError("SHA256SUMS does not describe the exact expected release files")
    return checksums


def _parse_buildinfo(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("Invalid BUILDINFO.txt manifest")
        result[key] = value
    expected = {"tag", "source_sha", "binary_version", "archive", "goos", "goarch", "cgo_enabled"}
    if set(result) != expected:
        raise ValueError("BUILDINFO.txt has unexpected or missing fields")
    return result


def _verify_release_files(archive: Path, checksums_path: Path, buildinfo_path: Path, tag: str) -> tuple[str, str]:
    checksums = _parse_checksums(checksums_path, {archive.name, buildinfo_path.name})
    for path in (archive, buildinfo_path):
        if _sha256(path) != checksums[path.name]:
            raise ValueError(f"SHA256 mismatch for {path.name}")
    info = _parse_buildinfo(buildinfo_path)
    if info["tag"] != tag:
        raise ValueError("BUILDINFO tag does not match requested release")
    if not SOURCE_SHA_PATTERN.fullmatch(info["source_sha"]):
        raise ValueError("BUILDINFO source_sha must be exactly 40 lowercase hex characters")
    version = f"{tag}+{info['source_sha']}"
    expected = {
        "binary_version": version,
        "archive": archive.name,
        "goos": "linux",
        "goarch": "amd64",
        "cgo_enabled": "0",
    }
    for key, value in expected.items():
        if info[key] != value:
            raise ValueError(f"BUILDINFO {key} does not match the requested release")
    return checksums[archive.name], version


def _read_observed_version(binary: Path) -> str:
    try:
        result = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, timeout=5,
            check=True, env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise ValueError(f"Installed Glance version check failed ({type(exc).__name__})") from None
    return result.stdout.strip()


def _existing_binary_matches(home: Path, archive_sha256: str, version: str) -> bool:
    binary = home / "bin/glance"
    provenance_path = home / "bin/glance.provenance.json"
    if not (binary.exists() or binary.is_symlink() or provenance_path.exists() or provenance_path.is_symlink()):
        return False
    refusal = "Existing Glance runtime is not this exact verified release; use native `chatglance runtime update` for explicit changes"
    if binary.is_symlink() or provenance_path.is_symlink() or not binary.is_file() or not provenance_path.is_file():
        raise ValueError(refusal)
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError(refusal) from None
    tag, source_sha = version.split("+", 1)
    expected = {
        "source": "verified local archive",
        "source_tag": tag,
        "source_revision": source_sha,
        "version": version,
        "archive_sha256": archive_sha256,
        "binary_sha256": _sha256(binary),
    }
    if provenance != expected or _read_observed_version(binary) != version:
        raise ValueError(refusal)
    return True


def install_glance(
    *, version: str = DEFAULT_GLANCE_VERSION, home: str | Path | None = None,
    repo: str = DEFAULT_GLANCE_REPO, dry_run: bool = False,
) -> GlanceInstallation:
    """Install or exactly reuse one verified maintained Go release, then initialize resources."""
    _require_supported_platform()
    root = runtime_home(home)
    binary = root / "bin/glance"
    config = root / "config/glance.yml"
    requested = str(version or DEFAULT_GLANCE_VERSION).strip()
    if dry_run:
        tag = DEFAULT_GLANCE_VERSION if requested == DEFAULT_GLANCE_VERSION else normalize_release_tag(requested)
        return GlanceInstallation("planned", tag, None, binary, config, ("chatglance", "runtime", "serve", "--runtime-home", str(root)))

    tag = resolve_requested_tag(requested, repo)
    archive_name = release_asset_name(tag)
    names = (archive_name, "SHA256SUMS", "BUILDINFO.txt")
    staging_parent = get_paths().home_dir / "chatup" / "staging"
    staging_parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if staging_parent.is_symlink() or not staging_parent.is_dir():
        raise ValueError("Unsafe Glance download staging directory")
    staging_parent.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix="glance-", dir=staging_parent) as temporary:
        staging = Path(temporary)
        for name in names:
            download_release_asset(release_asset_url(repo, tag, name), staging / name)
        archive = staging / archive_name
        archive_sha256, raw_version = _verify_release_files(
            archive, staging / "SHA256SUMS", staging / "BUILDINFO.txt", tag
        )
        reused = _existing_binary_matches(root, archive_sha256, raw_version)
        if not reused:
            install_verified_binary(archive, archive_sha256, root, version=raw_version)
    initialize(root)
    if not config.is_file() or config.is_symlink():
        raise ValueError("ChatGlance initialization did not provide a safe runtime config")
    return GlanceInstallation(
        "reused" if reused else "installed", tag, raw_version, binary, config,
        ("chatglance", "runtime", "serve", "--runtime-home", str(root)),
    )


def setup_glance(
    version: str = DEFAULT_GLANCE_VERSION,
    runtime_home: str | Path | None = None,
    dry_run: bool = False,
    interactive=None,
) -> GlanceInstallation:
    """Click-facing setup wrapper; setup never starts or enables the server."""
    del interactive
    try:
        result = install_glance(version=version, home=runtime_home, dry_run=dry_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    if result.status == "planned":
        click.echo(f"Glance setup plan: {result.tag} -> {result.binary}")
    else:
        click.echo(f"Glance binary: {result.binary}")
        click.echo(f"Glance config: {result.config}")
        click.echo(f"Glance release: {result.version} ({result.status})")
    click.echo("Native start command: " + shlex.join(result.start_command))
    click.echo("The server was not started and no service or public endpoint was created.")
    return result
