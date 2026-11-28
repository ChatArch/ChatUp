"""Install the native Antigravity CLI with Google's official bootstrapper."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Any
import urllib.request

INSTALLER_URL = "https://antigravity.google/cli/install.sh"
WINDOWS_INSTALLER_URL = "https://antigravity.google/cli/install.ps1"
DOWNLOAD_PAGE = "https://antigravity.google/download"


def plan_antigravity_cli_install(*, install_dir: str | Path | None = None) -> dict[str, Any]:
    """Describe installation without network access, writes or subprocesses."""
    system = platform.system()
    if system not in {"Darwin", "Linux", "Windows"}:
        raise RuntimeError(f"Antigravity CLI does not support {system}; see {DOWNLOAD_PAGE}.")
    if platform.machine().lower() not in {"arm64", "aarch64", "x86_64", "amd64"}:
        raise RuntimeError(f"Unsupported Antigravity CLI architecture: {platform.machine()}.")
    windows = system == "Windows"
    default = (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "agy" / "bin"
        if windows else Path.home() / ".local" / "bin"
    )
    directory = Path(install_dir).expanduser().absolute() if install_dir is not None else default
    binary = directory / ("agy.exe" if windows else "agy")
    return {
        "app": "Antigravity CLI", "platform": system,
        "url": WINDOWS_INSTALLER_URL if windows else INSTALLER_URL,
        "path": str(binary), "binary": str(binary), "install_dir": str(directory),
        "installer": "install.ps1" if windows else "install.sh",
    }


def _cache_dir() -> Path:
    home = Path(os.environ.get("CHATARCH_HOME", str(Path.home() / ".chatarch"))).expanduser()
    cache = home / "cache" / "antigravity"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _download_installer(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp Antigravity installer"})
    with urllib.request.urlopen(request, timeout=120) as response:
        if not response.url.startswith("https://"):
            raise RuntimeError("Refusing an Antigravity installer redirected away from HTTPS.")
        payload = response.read(1024 * 1024 + 1)
        expected = int(response.headers.get("Content-Length", "0"))
        if not payload or len(payload) > 1024 * 1024 or (expected and expected != len(payload)):
            raise RuntimeError("Antigravity bootstrapper download is empty, incomplete or too large.")
    destination.write_bytes(payload)


def _run(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "See installer output.").strip()
        raise RuntimeError(f"Antigravity command failed (exit {result.returncode}): {detail[-2000:]}")
    return result


def _verify_binary(binary: Path) -> str:
    if not binary.is_file() or (platform.system() != "Windows" and not os.access(binary, os.X_OK)):
        raise RuntimeError(f"Antigravity CLI executable is missing or not executable: {binary}.")
    result = _run([str(binary), "--version"], timeout=30)
    output = (result.stdout or result.stderr or "").strip()
    version = re.fullmatch(r"v?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", output)
    if not version:
        raise RuntimeError(f"Antigravity CLI version could not be verified at {binary}.")
    return version.group(1)


def setup_antigravity_cli(
    *, dry_run: bool = False, install_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Install and verify agy; preserve and verify an existing official target."""
    plan = plan_antigravity_cli_install(install_dir=install_dir)
    if dry_run:
        return {**plan, "status": "planned", "verified": False}
    binary = Path(plan["binary"])
    try:
        if binary.exists() or binary.is_symlink():
            try:
                version = _verify_binary(binary)
            except RuntimeError as exc:
                raise RuntimeError(f"Existing Antigravity CLI is invalid and was not overwritten: {exc}") from exc
            return {**plan, "status": "already_installed", "verified": True, "version": version}
        windows = plan["platform"] == "Windows"
        shell = (shutil.which("powershell") or shutil.which("pwsh")) if windows else shutil.which("bash")
        if not shell:
            name = "PowerShell" if windows else "Bash"
            raise RuntimeError(f"{name} is required for the official Antigravity CLI installer; see {DOWNLOAD_PAGE}.")
        with tempfile.TemporaryDirectory(prefix="install-", dir=_cache_dir()) as work:
            installer = Path(work) / plan["installer"]
            _download_installer(plan["url"], installer)
            command = [shell]
            if windows:
                command += ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]
            command += [str(installer), "--dir", plan["install_dir"]]
            _run(command, timeout=600)
        version = _verify_binary(binary)
        return {**plan, "status": "installed", "verified": True, "version": version}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Antigravity CLI installation or verification failed: {exc}") from exc
