"""Install the official ChatGPT desktop app (the successor to Codex App).

The OS package manager owns downloads, signatures, application paths and state.
This module never launches the app or changes Codex CLI configuration/auth.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any

CHATGPT_CASK = "homebrew/cask/chatgpt"
CHATGPT_STORE_ID = "9PLM9XGG6VKS"
DOWNLOAD_URL = "https://chatgpt.com/download/"
LINUX_GUIDE_URL = "https://learn.chatgpt.com/docs/linux/linux-app"


def plan_chatgpt_install(*, yes: bool = False) -> dict[str, Any]:
    """Return a side-effect-free install plan for the current OS.

    ``yes`` explicitly accepts Microsoft Store source/package agreements.
    Homebrew/WinGet resolve the current release and enforce OS/CPU requirements.
    Linux preview installation is deliberately not automated here.
    """
    system = platform.system()
    if system == "Darwin":
        manager = "brew"
        package = CHATGPT_CASK
        command = [manager, "install", "--cask", package]
        verify_command = [manager, "list", "--cask", "--versions", package]
        manager_url = "https://brew.sh/"
    elif system == "Windows":
        manager = "winget"
        package = CHATGPT_STORE_ID
        selector = ["--id", package, "--exact", "--source", "msstore", "--disable-interactivity"]
        command = [manager, "install", *selector, "--no-upgrade"]
        verify_command = [manager, "list", *selector]
        if yes:
            command += ["--accept-package-agreements", "--accept-source-agreements"]
            verify_command += ["--accept-source-agreements"]
        manager_url = "https://aka.ms/getwinget"
    else:
        guide = LINUX_GUIDE_URL if system == "Linux" else DOWNLOAD_URL
        raise RuntimeError(
            f"ChatUp automates ChatGPT desktop installation on macOS and Windows only; "
            f"current platform: {system}. Official downloads/instructions: {guide}"
        )
    return {
        "app": "ChatGPT (includes Codex)",
        "platform": system,
        "manager": manager,
        "manager_url": manager_url,
        "package": package,
        "command": command,
        "verify_command": verify_command,
        "download_url": DOWNLOAD_URL,
    }


def _is_installed(plan: dict[str, Any], executable: str) -> bool:
    result = subprocess.run(
        [executable, *plan["verify_command"][1:]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    if plan["manager"] == "brew":
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[0] != "chatgpt":
                continue
            if any(version.startswith("1.") for version in parts[1:]):
                raise RuntimeError(
                    "An older ChatGPT Classic cask is registered as chatgpt. "
                    "Migrate it manually with Homebrew before installing the new "
                    f"ChatGPT/Codex app: {DOWNLOAD_URL}"
                )
            return True
        return False
    # WinGet's exact Store selector exits zero only when a matching package exists.
    return True


def setup_chatgpt(*, dry_run: bool = False, yes: bool = False) -> dict[str, Any]:
    """Install if absent, then verify registration with the package manager.

    Returns the plan plus ``status`` (planned/already_installed/installed) and
    ``verified``. Dry-run does not require or invoke a package manager. Existing
    installations are not upgraded, overwritten or migrated; authentication and
    launching remain user actions. Raises RuntimeError on failed/unknown results.
    """
    plan = plan_chatgpt_install(yes=yes)
    result = {**plan, "status": "planned", "verified": False}
    if dry_run:
        return result
    executable = shutil.which(plan["manager"])
    if not executable:
        raise RuntimeError(
            f"Required package manager {plan['manager']} is not on PATH. "
            f"Install it first: {plan['manager_url']} or download manually: {DOWNLOAD_URL}"
        )
    try:
        if _is_installed(plan, executable):
            return {**result, "status": "already_installed", "verified": True}
        installed = subprocess.run(
            [executable, *plan["command"][1:]], check=False, timeout=1800,
        )
        if installed.returncode != 0:
            hint = " Use --yes to accept Store agreements." if plan["manager"] == "winget" and not yes else ""
            raise RuntimeError(
                f"ChatGPT installer failed (exit {installed.returncode}). "
                f"Check the package manager output above.{hint}"
            )
        if not _is_installed(plan, executable):
            raise RuntimeError(
                "ChatGPT installation verification failed. Check the package manager "
                "state before retrying; installation success is not confirmed."
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "ChatGPT package manager timed out; the installation state is unknown. "
            "Check the package manager before retrying."
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Cannot execute {plan['manager']}: {exc}") from exc
    return {**result, "status": "installed", "verified": True}
