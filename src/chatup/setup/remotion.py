"""Create a reproducible local Remotion project without overwriting user work."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

from chatup.utils.custom_logger import setup_logger

REMOTION_VERSION = "4.0.530"
DEPENDENCIES = {
    "@remotion/cli": REMOTION_VERSION,
    "remotion": REMOTION_VERSION,
    "react": "19.1.0",
    "react-dom": "19.1.0",
}
MARKER = ".chatup-remotion.json"
OWNERSHIP = {"schema": 1, "template": "remotion", "version": REMOTION_VERSION}
logger = logging.getLogger(__name__)


def _run(command: list[str], *, cwd: Path | None = None, timeout: int = 60) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise RuntimeError(f"{Path(command[0]).name} failed (exit {result.returncode}): {detail}")
    return result.stdout.strip()


def _find_browser(explicit: str | Path | None = None) -> str | None:
    if explicit is not None:
        path = Path(explicit).expanduser().absolute()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"Browser executable is not an executable file: {path}")
        return str(path)
    candidates = []
    if platform.system() == "Darwin":
        candidates = [directory / "Google Chrome.app/Contents/MacOS/Google Chrome"
                      for directory in (Path("/Applications"), Path.home() / "Applications")]
    elif platform.system() == "Windows":
        candidates = [Path(value) / "Google/Chrome/Application/chrome.exe"
                      for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
                      if (value := os.environ.get(name))]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if executable := shutil.which(name):
            candidates.append(Path(executable))
    return next((str(path) for path in candidates
                 if path.is_file() and os.access(path, os.X_OK)), None)


def _managed_target(target: Path) -> bool:
    if target.is_symlink():
        raise RuntimeError(f"Refusing a symlink project directory: {target}")
    if not target.exists():
        return False
    marker = target / MARKER
    try:
        owned = (target.is_dir() and not marker.is_symlink()
                 and json.loads(marker.read_text(encoding="utf-8")) == OWNERSHIP)
    except (OSError, ValueError):
        owned = False
    if not owned:
        raise RuntimeError(f"Refusing to overwrite an existing directory or file not managed by ChatUp: {target}")
    return True


def plan_remotion_setup(project_dir: str | Path, *, browser_executable=None) -> dict:
    target = Path(os.path.abspath(Path(project_dir).expanduser()))
    managed = _managed_target(target)
    return {"path": str(target), "version": REMOTION_VERSION, "managed": managed,
            "browser": _find_browser(browser_executable), "status": "planned"}


def _runtime() -> tuple[str, str]:
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Node.js >=18.12 and npm >=9 are required. Install them first with chatup nodejs.")
    for name, executable, minimum in (("Node.js", node, (18, 12, 0)), ("npm", npm, (9, 0, 0))):
        version = _run([executable, "--version"])
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version)
        if not match or tuple(map(int, match.groups())) < minimum:
            required = ".".join(map(str, minimum))
            raise RuntimeError(f"{name} >={required} is required; found {version}.")
    return node, npm


def _verify_project(target: Path, npm: str) -> None:
    try:
        package = json.loads((target / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((target / "package-lock.json").read_text(encoding="utf-8"))
        for data in (package, lock["packages"][""]):
            if (not isinstance(data, dict) or not isinstance(data.get("dependencies"), dict)
                    or any(data["dependencies"].get(name) != version for name, version in DEPENDENCIES.items())):
                raise ValueError("the project's pinned dependencies have changed")
        installed = json.loads(_run([npm, "ls", "--depth=0", "--json"], cwd=target))["dependencies"]
        if (not isinstance(installed, dict) or any(
                not isinstance(installed.get(name), dict) or installed[name].get("version") != version
                for name, version in DEPENDENCIES.items())):
            raise ValueError("installed dependency versions do not match the template")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Cannot verify Remotion project at {target}: {exc}. Existing files are preserved.") from exc


def setup_remotion(project_dir: str | Path, *, dry_run: bool = False,
                   browser_executable=None, log_level: str = "INFO") -> dict:
    global logger
    logger = setup_logger(__name__, log_level=log_level)
    try:
        plan = plan_remotion_setup(project_dir, browser_executable=browser_executable)
        if dry_run:
            return plan
        target = Path(plan["path"])
        logger.info("Checking Node.js and npm")
        _, npm = _runtime()
        if plan["managed"]:
            _verify_project(target, npm)
            return {**plan, "status": "already_initialized"}
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".chatup-remotion-", dir=target.parent))
        try:
            template = Path(__file__).parent / "assets" / "remotion"
            shutil.copytree(template, staging, dirs_exist_ok=True)
            logger.info("Installing locked Remotion dependencies in %s", target)
            _run([npm, "ci", "--ignore-scripts", "--include=optional", "--no-audit", "--no-fund"],
                 cwd=staging, timeout=1800)
            _verify_project(staging, npm)
            (staging / MARKER).write_text(json.dumps(OWNERSHIP, indent=2) + "\n", encoding="utf-8")
            if target.exists() or target.is_symlink():
                raise RuntimeError(f"Destination appeared during installation; refusing to overwrite {target}.")
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        return {**plan, "status": "created"}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Remotion setup failed: {exc}") from exc
