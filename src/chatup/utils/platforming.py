from __future__ import annotations

import os
import platform
from pathlib import Path

import click

WINDOWS = os.name == "nt"


def is_windows() -> bool:
    return WINDOWS


def current_platform_label() -> str:
    system = platform.system() or os.name
    machine = platform.machine() or "unknown"
    return f"{system} {machine}"


def executable_name(name: str) -> str:
    if WINDOWS and not name.lower().endswith(".exe"):
        return f"{name}.exe"
    return name


def chmod_private(path: Path) -> None:
    if WINDOWS:
        return
    try:
        path.chmod(0o600)
    except PermissionError:
        return


def chmod_private_dir(path: Path) -> None:
    if WINDOWS:
        return
    try:
        path.chmod(0o700)
    except PermissionError:
        return


def chmod_executable(path: Path) -> None:
    if WINDOWS:
        return
    path.chmod(0o755)


def user_bin_candidates(name: str) -> tuple[Path, ...]:
    candidates = [Path.home() / ".local" / "bin" / name]
    if WINDOWS:
        candidates.append(Path.home() / ".local" / "bin" / executable_name(name))
    return tuple(candidates)


def venv_python_path(venv_path: Path) -> Path:
    if WINDOWS:
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def venv_activate_hint(venv_path: Path) -> str:
    if WINDOWS:
        return str(venv_path / "Scripts" / "Activate.ps1")
    return f"source {venv_path / 'bin' / 'activate'}"


def require_non_windows(feature: str) -> None:
    if WINDOWS:
        raise click.ClickException(
            f"{feature} is not supported on Windows yet. Platform: {current_platform_label()}."
        )


def require_systemd(feature: str) -> None:
    if WINDOWS:
        raise click.ClickException(
            f"{feature} uses user-level systemd services, which are not available on Windows."
        )
