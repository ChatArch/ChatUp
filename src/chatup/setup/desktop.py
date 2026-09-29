"""Native installers for regular Google Chrome and the macOS iTerm2 app."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
from typing import Any
import urllib.request

from chatup.runtime._managed_artifact import safe_extract_zip
from chatup.utils.custom_logger import setup_logger

logger = logging.getLogger(__name__)

MAC_APPS = {
    "chrome": {
        "app": "Google Chrome",
        "bundle": "Google Chrome.app",
        "bundle_id": "com.google.Chrome",
        "team_id": "EQHXZ8M8AV",
        "url": "https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome.dmg",
        "format": "dmg",
    },
    "iterm": {
        "app": "iTerm2",
        "bundle": "iTerm.app",
        "bundle_id": "com.googlecode.iterm2",
        "team_id": "H7V7XYVQ7D",
        "url": "https://iterm2.com/downloads/stable/latest",
        "format": "zip",
    },
}
LINUX_PACKAGES = {
    "apt-get": ("deb", ["install"]),
    "dnf": ("rpm", ["install"]),
    "yum": ("rpm", ["install"]),
    "zypper": ("rpm", ["install"]),
}


def _mac_app_dirs() -> tuple[Path, Path]:
    return Path("/Applications"), Path.home() / "Applications"


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def plan_desktop_install(
    app: str, *, sudo: bool = False, yes: bool = False,
) -> dict[str, Any]:
    """Describe the current platform's installation without writes or processes."""
    spec = MAC_APPS[app]
    system = platform.system()
    plan = {"app": spec["app"], "platform": system}
    if app == "iterm" and system != "Darwin":
        raise RuntimeError(f"iTerm2 is supported on macOS only; current platform: {system}.")
    if system == "Darwin":
        if platform.machine().lower() not in {"arm64", "aarch64", "x86_64", "amd64"}:
            raise RuntimeError(f"Unsupported macOS architecture: {platform.machine()}.")
        directories = _mac_app_dirs()
        existing = next((d / spec["bundle"] for d in directories if (d / spec["bundle"]).exists()), None)
        directory = directories[0] if os.access(directories[0], os.W_OK) else directories[1]
        return {**plan, **spec, "method": "macos", "path": str(existing or directory / spec["bundle"])}
    if system == "Windows":
        selector = ["--id", "Google.Chrome", "--exact", "--source", "winget", "--disable-interactivity"]
        command = ["winget", "install", *selector, "--silent", "--no-upgrade"]
        verify = ["winget", "list", *selector]
        if yes:
            command += ["--accept-package-agreements", "--accept-source-agreements"]
            verify += ["--accept-source-agreements"]
        return {**plan, "method": "winget", "command": command, "verify_command": verify}
    if system == "Linux":
        if platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("Google Chrome for Linux requires x86_64; Google does not provide a Linux ARM package.")
        manager = next((name for name in LINUX_PACKAGES if shutil.which(name)), None)
        if not manager:
            raise RuntimeError("Google Chrome requires apt-get, dnf, yum or zypper on Linux. See https://www.google.com/chrome/.")
        extension, action = LINUX_PACKAGES[manager]
        filename = f"google-chrome-stable_current_{'amd64' if extension == 'deb' else 'x86_64'}.{extension}"
        command = [manager]
        if manager == "zypper" and yes:
            command += ["--non-interactive"]
        command += action
        if manager != "zypper" and yes:
            command += ["-y"]
        command += ["{package}"]
        if sudo and not _is_root():
            command.insert(0, "sudo")
        return {**plan, "method": "linux", "manager": manager, "command": command,
                "url": f"https://dl.google.com/linux/direct/{filename}", "filename": filename}
    raise RuntimeError(f"Google Chrome installation is not supported on {system}.")


def _run(command: list[str], *, capture: bool = True, timeout: int = 1800, check: bool = True):
    logger.debug("Running: %s", command)
    result = subprocess.run(
        command, capture_output=capture, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "See installer output.").strip()
        raise RuntimeError(f"{Path(command[0]).name} failed (exit {result.returncode}): {detail[-2000:]}")
    return result


def _download(url: str, destination: Path) -> None:
    logger.info("Downloading %s", url)
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp desktop installer"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        if not response.url.startswith("https://"):
            raise RuntimeError("Refusing a download redirected away from HTTPS.")
        total = 0
        expected = int(response.headers.get("Content-Length", "0"))
        limit = 1024 * 1024 * 1024
        if expected > limit:
            raise RuntimeError("Desktop installer exceeds the 1 GiB download limit.")
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            total += len(chunk)
            if total > limit:
                raise RuntimeError("Desktop installer exceeds the 1 GiB download limit.")
            output.write(chunk)
        if not total or (expected and total != expected):
            raise RuntimeError("Desktop installer download is incomplete; retry the command.")


def _cache_dir() -> Path:
    home = Path(os.environ.get("CHATARCH_HOME", str(Path.home() / ".chatarch"))).expanduser()
    cache = home / "cache" / "desktop"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _mac_bundle(plan: dict[str, Any], path: Path) -> dict[str, str]:
    try:
        with (path / "Contents" / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        executable_name = info.get("CFBundleExecutable", "")
        binary = path / "Contents" / "MacOS" / executable_name
        version = info.get("CFBundleShortVersionString", "")
        if (info.get("CFBundleIdentifier") != plan["bundle_id"] or not version
                or not executable_name or Path(executable_name).name != executable_name
                or not binary.is_file() or not os.access(binary, os.X_OK)):
            raise ValueError("bundle identity, version or executable is invalid")
        minimum = info.get("LSMinimumSystemVersion", "")
        current = platform.mac_ver()[0]
        if minimum and current:
            def version_tuple(value):
                return tuple(int(part) for part in value.split(".")) + (0,) * (3 - len(value.split(".")))
            if version_tuple(current) < version_tuple(minimum):
                raise ValueError(f"requires macOS {minimum} or later; current: {current}")
    except (OSError, ValueError, plistlib.InvalidFileException) as exc:
        raise RuntimeError(f"Cannot verify {plan['app']} at {path}: {exc}. Existing apps are never overwritten.") from exc
    requirement = f'=anchor apple generic and certificate leaf[subject.OU] = "{plan["team_id"]}"'
    _run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "-R", requirement, str(path)], timeout=120)
    return {"path": str(path), "binary": str(binary), "version": str(version)}


def _install_macos(plan: dict[str, Any]) -> dict[str, Any]:
    target = Path(plan["path"])
    if target.exists() or target.is_symlink():
        logger.info("Checking existing %s", target)
        return {**plan, **_mac_bundle(plan, target), "status": "already_installed", "verified": True}
    work = Path(tempfile.mkdtemp(prefix="install-", dir=_cache_dir()))
    mount = work / "volume"
    mounted = False
    try:
        archive = work / f"download.{plan['format']}"
        _download(plan["url"], archive)
        if plan["format"] == "dmg":
            mount.mkdir()
            _run(["/usr/bin/hdiutil", "attach", str(archive), "-mountpoint", str(mount),
                  "-nobrowse", "-readonly", "-noautoopen"], timeout=120)
            mounted = True
            source = mount / plan["bundle"]
        else:
            source = work / "unpacked" / plan["bundle"]
            safe_extract_zip(archive, source.parent, label=plan["app"])
        logger.info("Verifying %s publisher signature and app bundle", plan["app"])
        _mac_bundle(plan, source)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Stage on the target filesystem so the final app appears in one rename.
        with tempfile.TemporaryDirectory(prefix=".chatup-", dir=target.parent) as staging:
            staged = Path(staging) / plan["bundle"]
            logger.info("Installing %s", target)
            _run(["/usr/bin/ditto", str(source), str(staged)])
            _mac_bundle(plan, staged)
            if target.exists() or target.is_symlink():
                raise RuntimeError(f"App appeared during installation; refusing to overwrite {target}.")
            staged.rename(target)
        details = _mac_bundle(plan, target)
        return {**plan, **details, "status": "installed", "verified": True}
    finally:
        if mounted:
            detached = _run(["/usr/bin/hdiutil", "detach", str(mount)], timeout=120, check=False)
            if detached.returncode:
                _run(["/usr/bin/hdiutil", "detach", "-force", str(mount)], timeout=120, check=False)
        # Never recursively clean up a still-mounted disk image.
        if not os.path.ismount(mount):
            shutil.rmtree(work)
        else:
            logger.warning("Disk image still mounted at %s; installer cache retained at %s", mount, work)


def _linux_chrome() -> dict[str, str] | None:
    binary = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    if not binary:
        return None
    result = _run([binary, "--version"], timeout=30, check=False)
    match = re.match(r"Google Chrome (\d+(?:\.\d+)+)", result.stdout.strip())
    if result.returncode or not match:
        raise RuntimeError(f"Cannot verify regular Google Chrome at {binary}.")
    return {"binary": binary, "version": match.group(1)}


def _install_linux(plan: dict[str, Any], *, sudo: bool) -> dict[str, Any]:
    existing = _linux_chrome()
    if existing:
        return {**plan, **existing, "status": "already_installed", "verified": True}
    if not _is_root() and not sudo:
        raise RuntimeError("Installing Google Chrome on Linux requires root. Re-run: chatup chrome --sudo (optionally --yes).")
    if not _is_root() and not shutil.which("sudo"):
        raise RuntimeError("sudo is unavailable; run chatup chrome as root.")
    with tempfile.TemporaryDirectory(prefix="chrome-", dir=_cache_dir()) as staging:
        package = Path(staging) / plan["filename"]
        _download(plan["url"], package)
        command = [str(package) if arg == "{package}" else arg for arg in plan["command"]]
        logger.info("Installing Google Chrome with %s", plan["manager"])
        _run(command, capture=False)
    installed = _linux_chrome()
    if not installed:
        raise RuntimeError("Google Chrome installation verification failed: browser executable not found.")
    return {**plan, **installed, "status": "installed", "verified": True}


def _install_windows(plan: dict[str, Any]) -> dict[str, Any]:
    executable = shutil.which("winget")
    if not executable:
        raise RuntimeError("WinGet is required to install Google Chrome: https://aka.ms/getwinget")

    def installed():
        result = _run([executable, *plan["verify_command"][1:]], timeout=120, check=False)
        return result.returncode == 0 and re.search(r"\bGoogle\.Chrome\b", result.stdout) is not None

    if installed():
        return {**plan, "status": "already_installed", "verified": True}
    logger.info("Installing Google Chrome with WinGet; use --yes to accept source/package agreements")
    _run([executable, *plan["command"][1:]], capture=False)
    if not installed():
        raise RuntimeError("Google Chrome installation verification failed: no matching WinGet package record.")
    return {**plan, "status": "installed", "verified": True}


def setup_desktop_app(
    app: str, *, dry_run: bool = False, sudo: bool = False, yes: bool = False,
    log_level: str = "INFO",
) -> dict[str, Any]:
    """Install a native app if absent and verify it; never launch or upgrade it."""
    global logger
    logger = setup_logger(__name__, log_level=log_level)
    try:
        plan = plan_desktop_install(app, sudo=sudo, yes=yes)
        if dry_run:
            return {**plan, "status": "planned", "verified": False}
        logger.info("Checking %s installation on %s", plan["app"], plan["platform"])
        if plan["method"] == "macos":
            return _install_macos(plan)
        if plan["method"] == "linux":
            return _install_linux(plan, sudo=sudo)
        return _install_windows(plan)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        logger.error("%s installation failed: %s", MAC_APPS[app]["app"], exc)
        raise RuntimeError(f"{MAC_APPS[app]['app']} installation failed: {exc}") from exc
