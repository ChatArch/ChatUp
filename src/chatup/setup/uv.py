from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import click

from chatup.utils.custom_logger import setup_logger

DEFAULT_PYTHON_VERSION = "3.12"
DEFAULT_VENV_PATH = Path("~/.chatarch/venv")
UV_INSTALLER_URL = "https://astral.sh/uv/install.sh"

logger = setup_logger("setup_uv")


def _configure_logger(log_level: str = "INFO"):
    global logger
    logger = setup_logger("setup_uv", log_level=str(log_level).upper())
    return logger


def _display_command(command: list[str] | tuple[str, ...]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def _run_command(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    click.echo(f"Running: {_display_command(command)}")
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def _candidate_uv_paths() -> tuple[Path, ...]:
    return (
        Path.home() / ".local" / "bin" / "uv",
        Path.home() / ".cargo" / "bin" / "uv",
    )


def find_uv() -> str | None:
    uv = shutil.which("uv")
    if uv:
        return uv
    for candidate in _candidate_uv_paths():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def install_uv_with_official_script() -> str:
    command = ["sh", "-c", f"curl -LsSf {shlex.quote(UV_INSTALLER_URL)} | sh"]
    result = _run_command(command)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "uv installer failed").strip()
        raise click.ClickException(f"Failed to install uv: {message}")

    uv = find_uv()
    if not uv:
        raise click.ClickException(
            "uv installer finished, but `uv` was not found on PATH or in ~/.local/bin. "
            "Open a new shell or add the installer bin directory to PATH."
        )
    return uv


def ensure_uv_installed() -> str:
    uv = find_uv()
    if uv:
        click.echo(f"uv found: {uv}")
        return uv

    click.echo("uv not found; installing via the official uv installer script.")
    uv = install_uv_with_official_script()
    click.echo(f"uv installed: {uv}")
    return uv


def _venv_python_path(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _python_minor_version(python_bin: Path) -> str | None:
    if not python_bin.exists():
        return None
    result = subprocess.run(
        [str(python_bin), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _venv_has_pip(python_bin: Path) -> bool:
    if not python_bin.exists():
        return False
    result = subprocess.run(
        [str(python_bin), "-m", "pip", "--version"], capture_output=True, text=True
    )
    return result.returncode == 0


def is_chatarch_python_ready(venv_path: Path, python_version: str) -> bool:
    python_bin = _venv_python_path(venv_path)
    current_version = _python_minor_version(python_bin)
    return current_version == python_version and _venv_has_pip(python_bin)


def create_chatarch_python_env(
    uv_bin: str, venv_path: Path, python_version: str, *, force: bool = False
) -> None:
    install_result = _run_command([uv_bin, "python", "install", python_version])
    if install_result.returncode != 0:
        message = (install_result.stderr or install_result.stdout).strip()
        raise click.ClickException(f"Failed to install Python {python_version} via uv: {message}")

    command = [uv_bin, "venv", "--python", python_version, "--seed"]
    if force:
        command.extend(("--clear", "--force"))
    elif venv_path.exists():
        command.append("--allow-existing")
    command.append(str(venv_path))
    venv_result = _run_command(command)
    if venv_result.returncode != 0:
        message = (venv_result.stderr or venv_result.stdout).strip()
        raise click.ClickException(f"Failed to create ChatArch Python env at {venv_path}: {message}")


def setup_uv(
    venv: str | None = None,
    python_version: str = DEFAULT_PYTHON_VERSION,
    force: bool = False,
    log_level: str = "INFO",
) -> dict[str, str]:
    _configure_logger(log_level)
    target = Path(venv or str(DEFAULT_VENV_PATH)).expanduser()
    python_version = str(python_version).strip() or DEFAULT_PYTHON_VERSION

    uv_bin = ensure_uv_installed()
    click.echo(f"ChatArch Python env: {target}")
    click.echo(f"Requested Python: {python_version}")

    if is_chatarch_python_ready(target, python_version) and not force:
        click.echo("ChatArch Python environment already ready.")
        return {
            "uv": uv_bin,
            "venv": str(target),
            "python": str(_venv_python_path(target)),
            "python_version": python_version,
            "status": "ready",
        }

    python_bin = _venv_python_path(target)
    current_version = _python_minor_version(python_bin)
    if target.exists() and not force:
        if current_version is None:
            raise click.ClickException(
                f"Target path exists but is not a Python virtual environment: {target}. "
                "Pass --force to clear it or choose another --venv path."
            )
        if current_version != python_version:
            raise click.ClickException(
                f"Existing ChatArch Python env at {target} uses Python {current_version}, "
                f"but Python {python_version} was requested. Pass --force to recreate it "
                "or choose another --venv path."
            )
        click.echo("ChatArch Python environment exists but pip is missing; seeding pip with uv.")
    elif target.exists() and force:
        click.echo("Recreating existing ChatArch Python environment with uv.")
    else:
        click.echo("ChatArch Python environment not found; creating it with uv.")

    create_chatarch_python_env(uv_bin, target, python_version, force=force)

    if not is_chatarch_python_ready(target, python_version):
        raise click.ClickException(
            f"ChatArch Python env was created at {target}, but Python {python_version} with pip was not verified."
        )

    python_bin = _venv_python_path(target)
    click.echo(f"ChatArch Python environment ready: {target}")
    click.echo(f"Activate with: source {shlex.quote(str(target / 'bin' / 'activate'))}")
    click.echo(f"Verified pip: {python_bin} -m pip --version")
    return {
        "uv": uv_bin,
        "venv": str(target),
        "python": str(python_bin),
        "python_version": python_version,
        "status": "created",
    }
