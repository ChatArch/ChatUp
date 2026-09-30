"""Native installers for Chrome, Snipaste and supported macOS desktop apps."""
from __future__ import annotations

import logging
import hashlib
import base64
import json
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
        "winget_id": "Google.Chrome.EXE",
        "winget_scope": "user",
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
    "snipaste": {
        "app": "Snipaste",
        "winget_id": "liule.Snipaste",
        "bundle": "Snipaste.app",
        "bundle_id": "com.Snipaste",
        "team_id": "NGTL73P583",
        "url": "https://dl.snipaste.com/mac",
        "format": "dmg",
    },
    "blender": {
        "app": "Blender",
        "bundle": "Blender.app",
        "bundle_id": "org.blenderfoundation.blender",
        "team_id": "68UA947AUU",
        "url": "https://download.blender.org/release/Blender5.2/blender-5.2.2-macos-arm64.dmg",
        "format": "dmg",
        "architectures": ("arm64", "aarch64"),
        "download_version": "5.2.2",
        "sha256": "dc4125399b8bfefe283cc1624d6cfc7809d1cac20ace51072127eb371f31f210",
        "notarized": True,
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


def plan_desktop_install(app: str, *, sudo: bool = False, yes: bool = False) -> dict[str, Any]:
    """Describe the current platform's installation without writes or processes."""
    spec = MAC_APPS[app]
    system = platform.system()
    plan = {"app": spec["app"], "platform": system}
    if system != "Darwin" and app in {"iterm", "blender"}:
        raise RuntimeError(f"{spec['app']} is supported on macOS only; current platform: {system}.")
    if system not in {"Darwin", "Windows"} and app == "snipaste":
        raise RuntimeError(f"{spec['app']} is supported on macOS and Windows only; current platform: {system}.")
    if system == "Darwin":
        if platform.machine().lower() not in {"arm64", "aarch64", "x86_64", "amd64"}:
            raise RuntimeError(f"Unsupported macOS architecture: {platform.machine()}.")
        if spec.get("architectures") and platform.machine().lower() not in spec["architectures"]:
            raise RuntimeError(f"{spec['app']} installation supports Apple Silicon macOS only; current architecture: {platform.machine()}.")
        directories = _mac_app_dirs()
        existing = next((d / spec["bundle"] for d in directories if (d / spec["bundle"]).exists()), None)
        directory = directories[0] if os.access(directories[0], os.W_OK) else directories[1]
        return {**plan, **spec, "method": "macos", "path": str(existing or directory / spec["bundle"])}
    if system == "Windows":
        package_id = spec.get("winget_id")
        if not package_id:
            raise RuntimeError(f"{spec['app']} is supported on macOS only; current platform: {system}.")
        selector = ["--id", package_id, "--exact", "--source", "winget", "--disable-interactivity"]
        command = ["winget", "install", *selector, "--silent", "--no-upgrade"]
        if spec.get("winget_scope"):
            command += ["--scope", spec["winget_scope"]]
        verify = ["winget", "list", *selector]
        if yes:
            command += ["--accept-package-agreements", "--accept-source-agreements"]
            verify += ["--accept-source-agreements"]
        return {
            **plan,
            "method": "winget",
            "winget_id": package_id,
            "command": command,
            "verify_command": verify,
        }
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
    if plan.get("notarized"):
        _run(["/usr/sbin/spctl", "--assess", "--type", "execute", str(path)], timeout=120)
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
        if plan.get("sha256"):
            digest = hashlib.sha256()
            with archive.open("rb") as source_file:
                for block in iter(lambda: source_file.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != plan["sha256"]:
                raise RuntimeError(f"{plan['app']} download SHA-256 verification failed.")
            logger.info("Verified official SHA-256 for %s", plan["app"])
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
        source_details = _mac_bundle(plan, source)
        if plan.get("download_version") and source_details["version"] != plan["download_version"]:
            raise RuntimeError(f"Unexpected downloaded {plan['app']} version: {source_details['version']}.")
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


def _google_signed_file(path: Path) -> dict[str, str]:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not powershell:
        raise RuntimeError("PowerShell is required to verify Google's Authenticode signature.")
    # Encode the script and quote its sole path literal, including apostrophes.
    literal = str(path).replace("'", "''")
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$ProgressPreference = 'SilentlyContinue'; "
        "$env:PSModulePath = Join-Path $PSHOME 'Modules'; "
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        f"$file = Get-Item -LiteralPath '{literal}'; "
        "$sig = Get-AuthenticodeSignature -LiteralPath $file.FullName; "
        "$publisher = if ($sig.SignerCertificate) { "
        "$sig.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false) "
        "} else { '' }; "
        "@{status=[string]$sig.Status; publisher=$publisher; "
        "product=$file.VersionInfo.ProductName; version=$file.VersionInfo.ProductVersion; "
        "original=$file.VersionInfo.OriginalFilename} | ConvertTo-Json -Compress"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = _run([powershell, "-NoProfile", "-NonInteractive", "-OutputFormat", "Text",
                   "-EncodedCommand", encoded], timeout=120)
    details = json.loads(result.stdout.lstrip("\ufeff"))
    if not isinstance(details, dict) or details.get("status") != "Valid" or details.get("publisher") != "Google LLC":
        raise RuntimeError(f"Google Authenticode signature verification failed: {path}.")
    version = details.get("version", "")
    if (details.get("product") != "Google Chrome"
            or str(details.get("original", "")).lower() != "chrome.exe"
            or not isinstance(version, str) or not re.fullmatch(r"\d+(?:\.\d+){3}", version)):
        raise RuntimeError(f"Cannot verify installed Google Chrome identity/version: {path}.")
    return {"binary": str(path), "path": str(path), "version": version}


def _windows_chrome() -> dict[str, str] | None:
    for variable in ("LOCALAPPDATA", "PROGRAMW6432", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(variable)
        if root:
            binary = Path(root) / "Google/Chrome/Application/chrome.exe"
            if binary.exists():
                return _google_signed_file(binary)
    return None


def _install_windows(plan: dict[str, Any]) -> dict[str, Any]:
    is_chrome = plan["winget_id"] == "Google.Chrome.EXE"
    existing = _windows_chrome() if is_chrome else None
    if existing:
        return {**plan, **existing, "status": "already_installed", "verified": True}
    executable = shutil.which("winget")
    if not executable:
        raise RuntimeError(f"WinGet is required to install {plan['app']}: https://aka.ms/getwinget")

    def installed():
        result = _run([executable, *plan["verify_command"][1:]], timeout=120, check=False)
        return result.returncode == 0 and re.search(
            rf"(?<![\w.-]){re.escape(plan['winget_id'])}(?![\w.-])", result.stdout,
        ) is not None

    if installed():
        if is_chrome:
            raise RuntimeError("Google Chrome package record exists, but signed chrome.exe was not found.")
        return {**plan, "status": "already_installed", "verified": True}
    logger.info("Installing %s with WinGet; use --yes to accept source/package agreements", plan["app"])
    _run([executable, *plan["command"][1:]], capture=False)
    if not installed():
        raise RuntimeError(f"{plan['app']} installation verification failed: no matching WinGet package record.")
    details = _windows_chrome() if is_chrome else {}
    if is_chrome and not details:
        raise RuntimeError("Google Chrome installation verification failed: signed chrome.exe not found.")
    return {**plan, **details, "status": "installed", "verified": True}


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
