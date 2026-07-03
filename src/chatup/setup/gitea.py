from __future__ import annotations

import hashlib
import lzma
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import click

from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_gitea")

DEFAULT_GITEA_REPO = "ChatArch/gitea"
DEFAULT_GITEA_VERSION = "1.0.0"
DEFAULT_INSTALL_DIR = Path("~/.chatarch/bin")
DEFAULT_BINARY_NAME = "gitea.exe" if os.name == "nt" else "gitea"


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_gitea", log_level=str(log_level).upper())
    return logger


def _machine_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    if machine in {"i386", "i686", "x86"}:
        return "386"
    if machine == "riscv64":
        return "riscv64"
    raise click.ClickException(f"Unsupported machine architecture for Gitea release asset: {machine}")


def select_gitea_asset_name(version: str = DEFAULT_GITEA_VERSION) -> str:
    system = platform.system().lower()
    arch = _machine_arch()
    if system == "darwin":
        return f"gitea-{version}-darwin-10.12-{arch}.xz"
    if system == "linux":
        return f"gitea-{version}-linux-{arch}.xz"
    if system == "windows":
        return f"gitea-{version}-windows-4.0-{arch}.exe.xz"
    if system == "freebsd":
        return f"gitea-{version}-freebsd14-{arch}.xz"
    raise click.ClickException(f"Unsupported operating system for Gitea release asset: {system}")


def gitea_release_asset_url(repo: str, version: str, asset_name: str) -> str:
    version = version.removeprefix("v")
    return f"https://github.com/{repo}/releases/download/v{version}/{asset_name}"


def verify_sha256(path: Path, checksum_path: Path) -> None:
    expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise click.ClickException(
            f"Checksum verification failed for {path.name}: expected {expected}, got {actual}"
        )


def download_release_asset(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=120) as response:
        if response.status != 200:
            raise click.ClickException(f"Failed to download Gitea release asset: HTTP {response.status}")
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def decompress_xz(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with lzma.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    destination.chmod(0o755)


def install_gitea_release_binary(
    *,
    repo: str,
    version: str,
    install_dir: Path,
    binary_name: str,
    force: bool,
) -> Path:
    version = version.removeprefix("v")
    asset_name = select_gitea_asset_name(version)
    url = gitea_release_asset_url(repo, version, asset_name)
    target = install_dir / binary_name
    if target.exists() and not force:
        logger.info("Reusing existing Gitea binary at %s", target)
        return target

    install_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".chatup-gitea-", dir=install_dir) as tmp:
        archive = Path(tmp) / asset_name
        checksum = Path(tmp) / f"{asset_name}.sha256"
        unpacked = Path(tmp) / binary_name
        download_release_asset(url, archive)
        download_release_asset(f"{url}.sha256", checksum)
        verify_sha256(archive, checksum)
        decompress_xz(archive, unpacked)
        unpacked.replace(target)
    return target


def verify_gitea_binary(path: Path, version: str) -> str:
    result = subprocess.run(
        [str(path), "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise click.ClickException(f"Gitea binary verification failed: {output}")
    if f"version {version}" not in output:
        raise click.ClickException(
            f"Gitea binary version mismatch: expected {version}, got {output}"
        )
    return output


def setup_gitea(
    version: str = DEFAULT_GITEA_VERSION,
    repo: str = DEFAULT_GITEA_REPO,
    install_dir: str | Path = DEFAULT_INSTALL_DIR,
    binary_name: str = DEFAULT_BINARY_NAME,
    force: bool = False,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    version = version.removeprefix("v")
    logger.info("Start Gitea setup")
    usage = "Usage: chatup gitea [--version VERSION] [--install-dir PATH] [--force] [-i|-I]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    install_path = Path(install_dir).expanduser().resolve()
    target = install_gitea_release_binary(
        repo=repo,
        version=version,
        install_dir=install_path,
        binary_name=binary_name,
        force=force,
    )
    version_output = verify_gitea_binary(target, version)
    click.echo(f"Gitea installed: {target}")
    click.echo(version_output)
    logger.info("Gitea setup completed")
    return {"status": "installed", "path": str(target), "version_output": version_output}
