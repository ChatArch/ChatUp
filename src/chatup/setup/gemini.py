"""Install Google's Gemini CLI npm package without changing account settings."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import shutil
import subprocess
from typing import Any

import click

from chatup.setup.nodejs import ensure_nodejs_requirement, node_runtime_env, run_npm_command

NPM_PACKAGE = "@google/gemini-cli"
MIN_NODE_MAJOR = 20
INSTALLATION_DOCS = "https://geminicli.com/docs/get-started/installation/"


def plan_gemini_cli_install() -> dict[str, Any]:
    """Describe the npm installation without runtime probes or side effects."""
    system = platform.system()
    if system not in {"Darwin", "Linux", "Windows"}:
        raise RuntimeError(f"Gemini CLI installation does not support {system}; see {INSTALLATION_DOCS}.")
    return {
        "app": "Gemini CLI", "platform": system, "package": NPM_PACKAGE,
        "minimum_node_major": MIN_NODE_MAJOR, "url": INSTALLATION_DOCS,
        "command": ["npm", "install", "-g", NPM_PACKAGE],
    }


def _package_entry(package: Path) -> Path | None:
    metadata = package / "package.json"
    if not metadata.is_file():
        return None
    data = json.loads(metadata.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid official Gemini CLI package metadata: {metadata}.")
    binary = data.get("bin")
    relative = binary.get("gemini") if isinstance(binary, dict) else binary
    if (data.get("name") != NPM_PACKAGE or not isinstance(relative, str)
            or not relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or PureWindowsPath(relative).root
            or ".." in PurePosixPath(relative).parts or "\\" in relative):
        raise RuntimeError(f"Invalid official Gemini CLI package metadata: {metadata}.")
    entry = package / relative
    if not entry.is_file():
        raise RuntimeError(f"Gemini CLI package executable is missing: {entry}.")
    return entry


def _launcher_entry(launcher: str, *, system: str) -> Path:
    """Recognize official npm/Homebrew links and avoid executing unknown wrappers."""
    path = Path(launcher)
    if system == "Windows" and path.suffix.lower() in {".cmd", ".ps1"}:
        entry = _package_entry(path.parent / "node_modules" / "@google" / "gemini-cli")
        if entry is not None:
            return entry
    else:
        target = path.resolve(strict=True)
        for directory in target.parents:
            metadata = directory / "package.json"
            if not metadata.is_file():
                continue
            data = json.loads(metadata.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise RuntimeError(f"Invalid Gemini launcher package metadata: {metadata}.")
            if data.get("name") != NPM_PACKAGE:
                continue
            entry = _package_entry(directory)
            if entry is not None and entry.resolve(strict=True) == target:
                return entry
            break
    raise RuntimeError(
        f"Existing gemini launcher at {launcher} cannot be identified as {NPM_PACKAGE}; "
        f"it was not overwritten. Check its installation and PATH; see {INSTALLATION_DOCS}."
    )


def _require_launcher(env: dict[str, str], root: Path, *, system: str) -> str:
    launcher = shutil.which("gemini", path=env.get("PATH"))
    if launcher:
        return launcher
    expected = root.parent / "gemini.cmd" if system == "Windows" else root.parent.parent / "bin" / "gemini"
    raise RuntimeError(
        f"The Gemini CLI package is present, but gemini is not callable on PATH. "
        f"Ensure the launcher exists at {expected} and add {expected.parent} to PATH. "
        f"Repair a missing launcher with `npm install -g {NPM_PACKAGE}`. The package was preserved."
    )


def _verify(command: list[str], *, env: dict[str, str]) -> str:
    result = subprocess.run(
        [*command, "--version"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=60, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "No version output.").strip()
        raise RuntimeError(f"Gemini CLI verification failed (exit {result.returncode}): {detail[-2000:]}")
    version = re.fullmatch(r"v?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", (result.stdout or "").strip())
    if not version:
        raise RuntimeError("Gemini CLI version could not be verified; existing executables were not overwritten.")
    return version.group(1)


def _npm_root() -> Path:
    result = run_npm_command(["root", "-g"])
    root = (result.stdout or "").strip()
    if result.returncode or not root:
        detail = (result.stderr or result.stdout or "No global npm root returned.").strip()
        raise RuntimeError(f"Cannot locate the global npm package directory: {detail[-2000:]}")
    return Path(root)


def setup_gemini_cli(*, dry_run: bool = False) -> dict[str, Any]:
    """Install or verify Gemini CLI using ChatUp's shared Node/npm runtime."""
    plan = plan_gemini_cli_install()
    if dry_run:
        return {**plan, "status": "planned", "verified": False}
    try:
        runtime = ensure_nodejs_requirement(min_major=MIN_NODE_MAJOR, interactive=False, can_prompt=False)
        env = node_runtime_env(runtime)
        node = str(runtime["node_bin"])
        launcher = shutil.which("gemini", path=env.get("PATH"))
        if launcher:
            entry = _launcher_entry(launcher, system=plan["platform"])
            version = _verify([node, str(entry)], env=env)
            return {**plan, "status": "already_installed", "verified": True, "version": version, "binary": launcher}
        root = _npm_root()
        package = root / "@google" / "gemini-cli"
        entry = _package_entry(package)
        status = "already_installed"
        if entry is None:
            result = run_npm_command(plan["command"][1:])
            if result.returncode:
                detail = (result.stderr or result.stdout or "See npm output.").strip()
                raise RuntimeError(f"Gemini CLI npm installation failed (exit {result.returncode}): {detail[-2000:]}")
            entry = _package_entry(package)
            if entry is None:
                raise RuntimeError("npm finished but the official Gemini CLI package was not found.")
            status = "installed"
        launcher = _require_launcher(env, root, system=plan["platform"])
        entry = _launcher_entry(launcher, system=plan["platform"])
        version = _verify([node, str(entry)], env=env)
        return {**plan, "status": status, "verified": True, "version": version, "binary": launcher}
    except click.Abort as exc:
        raise RuntimeError("Gemini CLI requires Node.js >= 20 and npm. Run: chatup nodejs") from exc
    except click.ClickException as exc:
        raise RuntimeError(str(exc)) from exc
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Gemini CLI installation or verification failed: {exc}") from exc
