"""Plan and apply a same-user Linux X11 Computer Use runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import time
from typing import Any

from chatup import __version__


DRIVER_VERSION = "0.36.0"
DESKTOP_PACKAGES = (
    "tigervnc-standalone-server", "tigervnc-common", "xfce4-session", "xfwm4",
    "xfce4-panel", "xfdesktop4", "dbus-x11", "xauth", "x11-utils",
    "x11-xserver-utils", "xterm",
)
_DISPLAY = re.compile(r"^:([0-9]{1,3})$")
_x11_socket_dir = Path("/tmp/.X11-unix")


@dataclass(frozen=True)
class DesktopConnection:
    display: str
    xauthority: Path
    ownership: str
    state_source: Path | None = None
    dbus_address: str | None = None
    runtime_dir: str | None = None
    vnc_port: int | None = None
    service: str | None = None


@dataclass(frozen=True)
class ComputerUsePlan:
    home: Path
    runtime: Path
    target: dict[str, Any]
    desktop: DesktopConnection
    service_path: Path | None
    chrome: Path | None
    driver_reused: bool
    driver_source: Path | None
    actions: tuple[str, ...]
    security: tuple[str, ...]
    energy: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        def paths(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, dict):
                return {key: paths(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [paths(item) for item in value]
            return value
        return paths(asdict(self))


def _linux_distribution() -> str:
    values = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    except OSError:
        return "unknown"
    return values.get("ID", "unknown").lower()


def _supported_platform() -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Computer Use supports Debian/Ubuntu Linux x86_64 X11 only")
    if _linux_distribution() not in {"debian", "ubuntu"}:
        raise RuntimeError("Computer Use installer supports Debian/Ubuntu Linux x86_64 X11 only")


def _home(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    from chatenv.paths import get_paths

    return Path(get_paths().home_dir).expanduser().resolve()


def _socket_exists(display: str) -> bool:
    match = _DISPLAY.fullmatch(display)
    if not match:
        raise RuntimeError("Expected a local X11 display such as :20")
    try:
        return stat.S_ISSOCK((_x11_socket_dir / f"X{match.group(1)}").stat().st_mode)
    except FileNotFoundError:
        return False


def _socket_accepts_connection(display: str) -> bool:
    if not _socket_exists(display):
        return False
    number = _DISPLAY.fullmatch(display).group(1)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(2)
            probe.connect(str(_x11_socket_dir / f"X{number}"))
        return True
    except OSError:
        return False


def _checked_attached(display: str, xauthority: Path, *, state_source: Path | None = None,
                      dbus_address: str | None = None, runtime_dir: str | None = None) -> DesktopConnection:
    if not _socket_accepts_connection(display):
        raise RuntimeError("Selected desktop X11 socket is stale or missing")
    authority = xauthority.expanduser().resolve()
    if not authority.is_file() or authority.stat().st_uid != os.getuid():
        raise RuntimeError("Selected Xauthority is missing or has a different UID")
    return DesktopConnection(display, authority, "attached", state_source, dbus_address, runtime_dir)


def _desktop_from_state(path: Path) -> DesktopConnection:
    if not path.is_file() or path.stat().st_uid != os.getuid():
        raise RuntimeError("Desktop state must be a same-user file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("Desktop state is unreadable") from exc
    if data.get("uid") != os.getuid():
        raise RuntimeError("Desktop state UID mismatch")
    if data.get("hostname") not in (None, socket.gethostname()):
        raise RuntimeError("Desktop state host mismatch")
    display = data.get("DISPLAY") or data.get("display")
    xauthority = data.get("XAUTHORITY") or data.get("xauthority")
    if not xauthority:
        raise RuntimeError("Desktop state has no Xauthority")
    return _checked_attached(display, Path(xauthority), state_source=path,
                             dbus_address=data.get("DBUS_SESSION_BUS_ADDRESS"),
                             runtime_dir=data.get("XDG_RUNTIME_DIR"))


def _entrypoints(runtime: Path, service: str | None) -> dict[str, str]:
    return {mode: str(runtime / "bin" / f"chatup-computer-{mode}") for mode in
            ("mcp", "chrome", "terminal", "status", "desktop") if mode != "desktop" or service}


def _launcher_content(runtime: Path, metadata_path: Path, mode: str) -> str:
    command = " ".join(shlex.quote(str(part)) for part in
                       (runtime / "venv/bin/python", runtime / "libexec/entry.py", metadata_path, mode))
    return f'#!/bin/sh\nexec {command} "$@"\n'


def _service_content(runtime: Path, metadata_path: Path) -> str:
    command = " ".join(shlex.quote(str(part)) for part in
                       (runtime / "venv/bin/python", runtime / "libexec/entry.py", metadata_path, "desktop-supervisor"))
    return ("[Unit]\nDescription=ChatUp managed Xfce Computer Use desktop\n"
            "StartLimitIntervalSec=120s\nStartLimitBurst=3\n"
            "[Service]\nType=simple\nExecStart=" + command + "\nRestart=on-failure\nRestartSec=5s\n"
            "TimeoutStopSec=30s\nSendSIGKILL=no\nMemoryMax=2G\nTasksMax=256\n"
            "[Install]\nWantedBy=default.target\n")


def _owned_artifact(path: Path, content: str, *, executable: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Existing Computer Use artifact is not a regular file: {path}")
    details = path.stat()
    if (details.st_uid != os.getuid() or details.st_mode & 0o077
            or (executable and not details.st_mode & stat.S_IXUSR)
            or path.read_text(encoding="utf-8") != content):
        raise RuntimeError(f"Existing Computer Use artifact is not owned or has changed: {path}")
    return True


def _installed_desktop(runtime: Path, *, allow_incomplete: bool = False) -> DesktopConnection:
    path = runtime / "metadata.json"
    details = path.stat()
    if details.st_uid != os.getuid() or details.st_mode & 0o077:
        raise RuntimeError("Existing managed Computer Use metadata is not private")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        target = data["target"]
        desktop = data["desktop"]
        if target["hostname"] != socket.gethostname() or target["uid"] != os.getuid():
            raise RuntimeError("Existing managed Computer Use target mismatch")
        if (data["runtime"]["home"] != str(runtime)
                or data["runtime"]["driver_version"] != DRIVER_VERSION
                or not _verified_driver(runtime)):
            raise RuntimeError("Existing managed Computer Use runtime is unverified")
        if not Path(data["runtime"]["chrome"]).is_file():
            raise RuntimeError("Existing managed Computer Use Chrome is missing")
        display = desktop["display"]
        if not _DISPLAY.fullmatch(display):
            raise RuntimeError("Existing managed Computer Use display is invalid")
        authority = Path(desktop["xauthority"])
        ownership = desktop["ownership"]
        if ownership not in {"attached", "managed-new"}:
            raise RuntimeError("Existing managed Computer Use ownership is invalid")
        service = desktop.get("service")
        if ownership == "managed-new":
            expected_service = (f"chatup-computer-use-{__version__.replace('.', '-')}-"
                                f"{os.getuid()}-{display[1:]}.service")
            if service != expected_service:
                raise RuntimeError("Existing managed Computer Use service identity mismatch")
        elif service is not None:
            raise RuntimeError("Attached Computer Use metadata claims a service")
        expected = _entrypoints(runtime, service)
        if data["entrypoints"] != expected:
            raise RuntimeError("Existing managed Computer Use entrypoint identity mismatch")
        from chatup import computer_use_entry

        complete = _owned_artifact(runtime / "libexec/entry.py",
                                   Path(computer_use_entry.__file__).read_text(encoding="utf-8"), executable=True)
        for mode, launcher in expected.items():
            complete = _owned_artifact(Path(launcher), _launcher_content(runtime, path, mode),
                                       executable=True) and complete
        if ownership == "attached":
            attached = _checked_attached(display, authority, state_source=path,
                                         dbus_address=desktop.get("dbus_address"),
                                         runtime_dir=desktop.get("runtime_dir"))
            if not complete:
                if not allow_incomplete:
                    raise RuntimeError("Existing managed Computer Use entrypoints are incomplete")
                original_source = Path(desktop["state_source"]) if desktop.get("state_source") else None
                return DesktopConnection(display, attached.xauthority, "attached", original_source,
                                         attached.dbus_address, attached.runtime_dir)
            return DesktopConnection(display, attached.xauthority, "installed-attached", path,
                                     attached.dbus_address, attached.runtime_dir)
        service_path = Path.home() / ".config/systemd/user" / service
        complete = _owned_artifact(service_path, _service_content(runtime, path), executable=False) and complete
        if not complete:
            if not allow_incomplete:
                raise RuntimeError("Existing managed Computer Use service or entrypoints are incomplete")
            return DesktopConnection(display, authority, "managed-new", None,
                                     vnc_port=desktop.get("vnc_port"), service=service)
        if _socket_exists(display) and not _socket_accepts_connection(display):
            raise RuntimeError("Existing managed Computer Use X11 socket is stale")
        return DesktopConnection(display, authority, "managed-existing", path,
                                 vnc_port=desktop.get("vnc_port"), service=service)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError("Existing managed Computer Use metadata is invalid") from exc


def _free_display() -> str:
    for number in range(20, 100):
        display = f":{number}"
        if not _socket_exists(display) and not Path(f"/tmp/.X{number}-lock").exists():
            return display
    raise RuntimeError("No free managed X11 display in :20..:99")


def _verified_driver(runtime: Path) -> bool:
    binary = runtime / "venv/bin/cua-driver"
    python = runtime / "venv/bin/python"
    if (not binary.is_file() or not os.access(binary, os.X_OK) or binary.stat().st_uid != os.getuid()
            or not python.is_file() or not os.access(python, os.X_OK)):
        return False
    for metadata in (runtime / "venv").glob("lib*/python*/site-packages/cua_driver-*.dist-info/METADATA"):
        try:
            fields = dict(line.split(": ", 1) for line in metadata.read_text(encoding="utf-8").splitlines()
                          if line.startswith(("Name: ", "Version: ")))
            owner = metadata.stat().st_uid
        except (OSError, ValueError):
            continue
        if (owner == os.getuid()
                and fields.get("Name", "").lower().replace("_", "-") == "cua-driver"
                and fields.get("Version") == DRIVER_VERSION):
            return True
    return False


def _desktop_packages_missing() -> bool:
    commands = ("Xtigervnc", "xfce4-session", "xfwm4", "dbus-run-session", "xauth",
                "xdpyinfo", "xset", "xterm")
    return any(shutil.which(name) is None for name in commands) or (
        shutil.which("tigervncpasswd") is None and shutil.which("vncpasswd") is None)


def plan_computer_use(*, home: Path | None = None, display: str | None = None,
                      xauthority: Path | None = None, state: Path | None = None) -> ComputerUsePlan:
    """Discover local files and OS facts only. Never run a process or create state."""
    _supported_platform()
    if state is not None and (display is not None or xauthority is not None):
        raise RuntimeError("Use --state or --display with --xauthority, not both")
    if (display is None) != (xauthority is None):
        raise RuntimeError("--display and --xauthority must be selected together")
    managed_home = _home(home)
    runtime = managed_home / "computer-use" / f"chatup-{__version__}"
    target = {"hostname": socket.gethostname(), "uid": os.getuid(), "platform": "linux-x86_64",
              "distribution": _linux_distribution()}
    installed_path = runtime / "metadata.json"
    if state is not None:
        selected_state = state.expanduser().resolve()
        desktop = (_installed_desktop(runtime, allow_incomplete=True) if selected_state == installed_path
                   else _desktop_from_state(selected_state))
    elif display is not None and xauthority is not None:
        desktop = _checked_attached(display, xauthority)
    elif installed_path.is_file():
        desktop = _installed_desktop(runtime, allow_incomplete=True)
    else:
        legacy_state = managed_home / "computer-use/run/desktop.env.json"
        if legacy_state.is_file() and legacy_state.stat().st_uid == os.getuid():
            try:
                desktop = _desktop_from_state(legacy_state)
            except RuntimeError:
                desktop = None
        else:
            desktop = None
        if desktop is None and os.environ.get("XDG_SESSION_TYPE", "x11").lower() == "x11":
            session_display = os.environ.get("DISPLAY", "")
            if _DISPLAY.fullmatch(session_display):
                session_auth = Path(os.environ.get("XAUTHORITY") or Path.home() / ".Xauthority")
                try:
                    desktop = _checked_attached(session_display, session_auth)
                except RuntimeError:
                    pass
        if desktop is None:
            selected = _free_display()
            desktop = DesktopConnection(selected, runtime / "run/Xauthority", "managed-new",
                                        vnc_port=5900 + int(selected[1:]),
                                        service=f"chatup-computer-use-{__version__.replace('.', '-')}-{os.getuid()}-{selected[1:]}.service")
    chrome_name = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    chrome = Path(chrome_name).resolve() if chrome_name else None
    service_path = (Path.home() / ".config/systemd/user" / desktop.service) if desktop.service else None
    legacy_runtime = managed_home / "computer-use"
    driver_source = (runtime / "venv" if _verified_driver(runtime) else
                     legacy_runtime / "venv" if _verified_driver(legacy_runtime) else None)
    driver_reused = driver_source is not None
    actions = []
    if desktop.ownership == "managed-new":
        if _desktop_packages_missing():
            actions.append("sudo apt-get install -y --no-install-recommends " + " ".join(DESKTOP_PACKAGES))
        actions.append(f"Create private Xfce/TigerVNC user session on {desktop.display}; VNC 127.0.0.1:{desktop.vnc_port} with password authentication")
        actions.append(f"Create and start owned user service {desktop.service}")
    elif desktop.ownership == "managed-existing":
        actions.append(f"Reuse owned user service {desktop.service}; enable and start it if stopped")
    else:
        if desktop.ownership == "attached" and not shutil.which("xterm"):
            actions.append("sudo apt-get install -y --no-install-recommends xterm for the terminal entrypoint")
        actions.append(f"Attach to same-user X11 {desktop.display}; leave its service and lifecycle with the current owner")
    actions.append("Reuse installed ordinary Google Chrome and its default profile" if chrome or desktop.ownership in {"managed-existing", "installed-attached"} else
                   "Install ordinary Google Chrome via setup_desktop_app('chrome') (official download and sudo apt-get package install); preserve default profile")
    actions.append(f"Reuse verified same-user cua-driver 0.36.0 from {driver_source}" if driver_reused else
                   "Create dedicated venv and install official PyPI cua-driver==0.36.0 after apply")
    if desktop.ownership not in {"managed-existing", "installed-attached"}:
        actions.append(f"Write namespaced target metadata and MCP/Chrome/terminal/status entrypoints under {runtime}")
    return ComputerUsePlan(
        managed_home, runtime, target, desktop, service_path, chrome, driver_reused, driver_source, tuple(actions),
        ("Entrypoints pin hostname, UID, display and Xauthority; stale connections refuse without fallback.",
         "VNC is loopback-only and authenticated; state and credentials are private.",
         "No Agent config, global driver command, firewall, public port or browser profile migration is changed."),
        ("An attached desktop keeps its existing power and lifecycle policy." if desktop.ownership in {"attached", "installed-attached"} else
         "The owned Xfce/TigerVNC user service remains active until stopped and uses CPU/memory.",
         "The owned session disables screen blanking and DPMS while running." if desktop.ownership in {"managed-new", "managed-existing"} else
         "No display power settings are changed by attachment."),
    )


def _safe_env() -> dict[str, str]:
    env = {"HOME": str(Path.home()), "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
           "PIP_CONFIG_FILE": "/dev/null", "PIP_NO_INPUT": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
           "PYTHONNOUSERSITE": "1"}
    runtime_dir = Path(f"/run/user/{os.getuid()}")
    if runtime_dir.is_dir() and runtime_dir.stat().st_uid == os.getuid():
        env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    return env


def _run(command: list[str], *, timeout: int = 1800) -> None:
    subprocess.run(command, check=True, timeout=timeout, env=_safe_env())


def _write_owned(path: Path, content: str, *, mode: int) -> None:
    if path.exists() or path.is_symlink():
        if path.is_file() and path.stat().st_uid == os.getuid() and path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"Refusing to overwrite existing Computer Use path: {path}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
    path.chmod(mode)


def _ensure_private_directory(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlinked Computer Use state directory: {path}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    details = path.stat()
    if details.st_uid != os.getuid() or not stat.S_ISDIR(details.st_mode) or details.st_mode & 0o077:
        raise RuntimeError(f"Computer Use state directory must be private and same-user: {path}")


def _venv_receipt_content(plan: ComputerUsePlan) -> str:
    return json.dumps({"hostname": plan.target["hostname"], "uid": plan.target["uid"],
                       "runtime": str(plan.runtime), "version": DRIVER_VERSION}, sort_keys=True) + "\n"


def apply_computer_use(plan: ComputerUsePlan) -> dict[str, Any]:
    """Apply a completed plan as the ordinary user; sudo is only for apt packages."""
    if socket.gethostname() != plan.target["hostname"] or os.getuid() != plan.target["uid"]:
        raise RuntimeError("Computer Use target changed since planning")
    _supported_platform()
    if os.geteuid() == 0:
        raise RuntimeError("Run Computer Use as the ordinary desktop user, not root")
    desktop = plan.desktop
    if desktop.ownership in {"managed-existing", "installed-attached"}:
        if _installed_desktop(plan.runtime) != desktop:
            raise RuntimeError("Existing managed Computer Use state changed since planning")
        if desktop.ownership == "managed-existing" and not _socket_accepts_connection(desktop.display):
            _run(["systemctl", "--user", "daemon-reload"], timeout=15)
            _run(["systemctl", "--user", "enable", "--now", desktop.service], timeout=45)
            for _ in range(100):
                if _socket_accepts_connection(desktop.display):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("Owned Computer Use desktop did not become ready")
        metadata_path = plan.runtime / "metadata.json"
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return {"target": data["target"], "desktop": data["desktop"],
                "metadata": str(metadata_path), "entrypoints": data["entrypoints"],
                "driver_version": DRIVER_VERSION}
    if desktop.ownership == "attached":
        _checked_attached(desktop.display, desktop.xauthority)
        if desktop.state_source is not None and _desktop_from_state(desktop.state_source) != desktop:
            raise RuntimeError("Selected desktop state changed since planning")
    elif _socket_exists(desktop.display) or Path(f"/tmp/.X{desktop.display[1:]}-lock").exists():
        raise RuntimeError("Selected managed desktop display became occupied")
    previous_umask = os.umask(0o077)
    try:
        return _apply_prechecked(plan)
    finally:
        os.umask(previous_umask)


def _apply_prechecked(plan: ComputerUsePlan) -> dict[str, Any]:
    desktop = plan.desktop
    if desktop.ownership == "managed-new" and _desktop_packages_missing():
        if not shutil.which("sudo"):
            raise RuntimeError("sudo is needed for the planned Debian/Ubuntu desktop packages")
        _run(["sudo", "apt-get", "install", "-y", "--no-install-recommends", *DESKTOP_PACKAGES])
    if desktop.ownership == "attached" and not shutil.which("xterm"):
        if not shutil.which("sudo"):
            raise RuntimeError("sudo is needed for the planned xterm package")
        _run(["sudo", "apt-get", "install", "-y", "--no-install-recommends", "xterm"])
    from chatup.setup.desktop import setup_desktop_app
    from unittest.mock import patch

    with patch.dict(os.environ, {**_safe_env(), "CHATARCH_HOME": str(plan.home)}, clear=True):
        chrome_result = setup_desktop_app("chrome", sudo=True)
    chrome = chrome_result.get("binary") or (str(plan.chrome) if plan.chrome else None)
    if not chrome:
        raise RuntimeError("Regular Google Chrome did not verify after installation")
    runtime = plan.runtime
    _ensure_private_directory(runtime)
    if not _verified_driver(runtime):
        venv = runtime / "venv"
        receipt = runtime / "venv-install.json"
        if plan.driver_source and plan.driver_source != venv:
            if venv.exists() or venv.is_symlink() or receipt.exists() or receipt.is_symlink():
                raise RuntimeError("Existing unverified managed venv or receipt will not be overwritten")
            if plan.driver_source != plan.home / "computer-use/venv" or not _verified_driver(plan.home / "computer-use"):
                raise RuntimeError("Previously verified local cua-driver changed since planning")
            venv.symlink_to(plan.driver_source, target_is_directory=True)
        else:
            expected_receipt = _venv_receipt_content(plan)
            if venv.exists() or venv.is_symlink():
                if not _owned_artifact(receipt, expected_receipt, executable=False):
                    raise RuntimeError("Existing unverified managed venv has no installer receipt")
                if venv.is_symlink() or not venv.is_dir():
                    raise RuntimeError("Existing unverified managed venv is not a private directory")
                _ensure_private_directory(venv)
            elif receipt.exists() or receipt.is_symlink():
                _owned_artifact(receipt, expected_receipt, executable=False)
            else:
                _write_owned(receipt, expected_receipt, mode=0o600)
            if not (venv / "bin/python").is_file():
                _run([sys.executable, "-m", "venv", str(venv)])
            _ensure_private_directory(venv)
            _run([str(venv / "bin/python"), "-m", "pip", "install", "--index-url",
                  "https://pypi.org/simple", f"cua-driver=={DRIVER_VERSION}"])
        if not _verified_driver(runtime):
            raise RuntimeError("Official cua-driver installation could not be verified")
    # cua-driver also writes ~/.cua-driver; its own HOME must be managed and private.
    for state_dir in (runtime / "driver-home", runtime / "driver", runtime / "driver/telemetry"):
        _ensure_private_directory(state_dir)
    from chatup import computer_use_entry

    entry = runtime / "libexec/entry.py"
    _write_owned(entry, Path(computer_use_entry.__file__).read_text(encoding="utf-8"), mode=0o700)
    metadata_path = runtime / "metadata.json"
    desktop_metadata = {"display": desktop.display, "xauthority": str(desktop.xauthority),
                        "ownership": desktop.ownership, "state_source": str(desktop.state_source) if desktop.state_source else None,
                        "dbus_address": desktop.dbus_address, "runtime_dir": desktop.runtime_dir,
                        "vnc_port": desktop.vnc_port, "service": desktop.service}
    entrypoints = _entrypoints(runtime, desktop.service)
    metadata = {"target": plan.target, "desktop": desktop_metadata,
                "runtime": {"home": str(runtime), "driver_version": DRIVER_VERSION,
                            "chrome": str(chrome), "terminal": shutil.which("xterm")},
                "entrypoints": entrypoints}
    for mode, launcher in entrypoints.items():
        _write_owned(Path(launcher), _launcher_content(runtime, metadata_path, mode), mode=0o700)
    if desktop.service:
        if plan.service_path is None:
            raise RuntimeError("Managed desktop has no service path")
        _write_owned(plan.service_path, _service_content(runtime, metadata_path), mode=0o600)
    # This is the installed-state publication point: all referenced files exist first.
    _write_owned(metadata_path, json.dumps(metadata, indent=2, sort_keys=True) + "\n", mode=0o600)
    _installed_desktop(runtime)
    if desktop.service:
        _run(["systemctl", "--user", "daemon-reload"], timeout=15)
        _run(["systemctl", "--user", "enable", "--now", desktop.service], timeout=45)
    return {"target": plan.target, "desktop": desktop_metadata,
            "metadata": str(metadata_path), "entrypoints": entrypoints, "driver_version": DRIVER_VERSION}
