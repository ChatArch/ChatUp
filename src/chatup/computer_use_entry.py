"""Standalone, stdlib-only entry copied into a managed Computer Use runtime."""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time


X11_SOCKET_DIR = Path("/tmp/.X11-unix")
_DISPLAY = re.compile(r"^:([0-9]{1,3})$")


def checked_target(metadata: dict) -> None:
    """Refuse a launcher copied to a different host or user."""
    target = metadata.get("target", {})
    if target.get("hostname") != socket.gethostname():
        raise RuntimeError("Computer Use target host mismatch")
    if target.get("uid") != os.getuid():
        raise RuntimeError("Computer Use target UID mismatch")


def checked_connection(metadata: dict) -> dict[str, str]:
    """Refuse stale/unknown X11 targets; never substitute the caller's DISPLAY."""
    checked_target(metadata)
    desktop = metadata.get("desktop", {})
    display = desktop.get("display")
    match = _DISPLAY.fullmatch(display or "")
    if not match:
        raise RuntimeError("Computer Use has no pinned local X11 display")
    authority = Path(desktop.get("xauthority") or "")
    if not authority.is_absolute() or not authority.is_file():
        raise RuntimeError("Computer Use Xauthority is missing")
    if authority.stat().st_uid != os.getuid():
        raise RuntimeError("Computer Use Xauthority UID mismatch")
    display_socket = X11_SOCKET_DIR / f"X{match.group(1)}"
    try:
        connected = stat.S_ISSOCK(display_socket.stat().st_mode)
    except FileNotFoundError:
        connected = False
    if not connected:
        raise RuntimeError("Computer Use X11 socket is stale or missing")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(2)
            probe.connect(str(display_socket))
    except OSError as exc:
        raise RuntimeError("Computer Use X11 connection is stale or unavailable") from exc
    result = {"DISPLAY": display, "XAUTHORITY": str(authority)}
    for key, name in (("dbus_address", "DBUS_SESSION_BUS_ADDRESS"),
                      ("runtime_dir", "XDG_RUNTIME_DIR")):
        if desktop.get(key):
            result[name] = desktop[key]
    if desktop.get("ownership") == "managed-new":
        runtime = Path(metadata["runtime"]["home"])
        session = runtime / "run/desktop-session.json"
        try:
            details = session.stat()
            if details.st_uid != os.getuid() or details.st_mode & 0o077:
                raise RuntimeError("Managed desktop session state is not private")
            state = json.loads(session.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("Managed desktop session is not ready") from exc
        if (state.get("hostname") != socket.gethostname() or state.get("uid") != os.getuid()
                or state.get("display") != display or not state.get("dbus_address")):
            raise RuntimeError("Managed desktop session target mismatch")
        result["DBUS_SESSION_BUS_ADDRESS"] = state["dbus_address"]
        if state.get("runtime_dir"):
            result["XDG_RUNTIME_DIR"] = state["runtime_dir"]
    return result


def _read_metadata(path: Path) -> dict:
    details = path.stat()
    if details.st_uid != os.getuid() or details.st_mode & 0o077:
        raise RuntimeError("Computer Use metadata must be private and owned by this user")
    return json.loads(path.read_text(encoding="utf-8"))


def _child_env(metadata: dict, connection: dict[str, str]) -> dict[str, str]:
    import pwd

    user = pwd.getpwuid(os.getuid())
    runtime = Path(metadata["runtime"]["home"])
    env = {
        "HOME": user.pw_dir,
        "USER": user.pw_name,
        "LOGNAME": user.pw_name,
        "LANG": "C.UTF-8",
        "PATH": f"{runtime / 'venv/bin'}:/usr/local/bin:/usr/bin:/bin",
    }
    env.update(connection)
    runtime_dir = Path(f"/run/user/{os.getuid()}")
    if "XDG_RUNTIME_DIR" not in env and runtime_dir.is_dir() and runtime_dir.stat().st_uid == os.getuid():
        env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    return env


def _verified_driver(runtime: Path) -> bool:
    binary = runtime / "venv/bin/cua-driver"
    python = runtime / "venv/bin/python"
    if (not binary.is_file() or not os.access(binary, os.X_OK) or binary.stat().st_uid != os.getuid()
            or not python.is_file() or not os.access(python, os.X_OK)):
        return False
    for path in (runtime / "venv").glob("lib*/python*/site-packages/cua_driver-*.dist-info/METADATA"):
        try:
            fields = dict(line.split(": ", 1) for line in path.read_text(encoding="utf-8").splitlines()
                          if line.startswith(("Name: ", "Version: ")))
            if (path.stat().st_uid == os.getuid() and fields.get("Name", "").lower().replace("_", "-") == "cua-driver"
                    and fields.get("Version") == "0.36.0"):
                return True
        except (OSError, ValueError):
            continue
    return False


def _desktop_session(metadata: dict) -> None:
    """Run inside dbus-run-session and publish its private connection details."""
    checked_target(metadata)
    desktop = metadata["desktop"]
    if desktop.get("ownership") != "managed-new" or os.environ.get("DISPLAY") != desktop["display"]:
        raise RuntimeError("Managed desktop session target mismatch")
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    if not address:
        raise RuntimeError("Managed desktop session has no D-Bus address")
    runtime = Path(metadata["runtime"]["home"])
    state = runtime / "run/desktop-session.json"
    state.write_text(json.dumps({"hostname": socket.gethostname(), "uid": os.getuid(),
                                 "display": desktop["display"], "dbus_address": address,
                                 "runtime_dir": os.environ.get("XDG_RUNTIME_DIR")}) + "\n", encoding="utf-8")
    state.chmod(0o600)
    os.execvpe("xfce4-session", ["xfce4-session"], dict(os.environ))


def _run_client(metadata: dict, mode: str, args: list[str]) -> None:
    connection = checked_connection(metadata)
    runtime = Path(metadata["runtime"]["home"])
    env = _child_env(metadata, connection)
    if mode == "mcp":
        driver = runtime / "venv/bin/cua-driver"
        if not _verified_driver(runtime):
            raise RuntimeError("Verified managed cua-driver is missing")
        driver_home = runtime / "driver-home"
        if driver_home.is_symlink() or not driver_home.is_dir():
            raise RuntimeError("Private managed cua-driver HOME is missing")
        details = driver_home.stat()
        if details.st_uid != os.getuid() or details.st_mode & 0o077:
            raise RuntimeError("Managed cua-driver HOME is not private or same-user")
        env.update({
            "HOME": str(driver_home),
            "CUA_DRIVER_HOME": str(runtime / "driver"),
            "CUA_DRIVER_RS_HOME": str(runtime / "driver"),
            "CUA_DRIVER_TELEMETRY_HOME": str(runtime / "driver/telemetry"),
            "CUA_DRIVER_RS_TELEMETRY_ENABLED": "false",
            "CUA_TELEMETRY_ENABLED": "false",
            "CUA_DRIVER_PERMISSION_MODE": "standard",
            "CUA_DRIVER_RS_UPDATE_CHECK": "false",
        })
        command = [str(driver), "mcp", "--direct", "--no-overlay", *args]
    elif mode == "chrome":
        if any(arg.startswith("-") for arg in args):
            raise RuntimeError("Chrome flags are not accepted by this launcher")
        binary = metadata["runtime"].get("chrome")
        if not binary or not Path(binary).is_file():
            raise RuntimeError("Regular Google Chrome is missing")
        command = [binary, "--new-window", *(args or ["about:blank"])]
    elif mode == "terminal":
        if args:
            raise RuntimeError("Terminal launcher takes no arguments")
        binary = metadata["runtime"].get("terminal")
        if not binary or not Path(binary).is_file():
            raise RuntimeError("xterm is missing")
        command = [binary, "-title", "Computer Use Terminal", "-e", "/bin/bash", "--noprofile", "--norc"]
    else:
        raise RuntimeError("Unknown Computer Use entrypoint")
    os.chdir(env["HOME"])
    os.execve(command[0], command, env)


def _start_desktop(metadata: dict) -> None:
    """Own only a new private TigerVNC/Xfce session; systemd owns cleanup."""
    checked_target(metadata)
    desktop = metadata["desktop"]
    if desktop.get("ownership") != "managed-new":
        raise RuntimeError("Attached desktop lifecycle belongs to its original owner")
    match = _DISPLAY.fullmatch(desktop["display"])
    if not match:
        raise RuntimeError("Invalid managed display")
    number = match.group(1)
    if (X11_SOCKET_DIR / f"X{number}").exists() or Path(f"/tmp/.X{number}-lock").exists():
        raise RuntimeError("Selected X11 display is occupied")
    runtime = Path(metadata["runtime"]["home"])
    os.umask(0o077)
    for name in ("run", "secrets", "logs", "desktop/config", "desktop/data", "desktop/cache", "driver"):
        (runtime / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    xauthority = Path(desktop["xauthority"])
    session_state = runtime / "run/desktop-session.json"
    if session_state.exists():
        if session_state.stat().st_uid != os.getuid():
            raise RuntimeError("Managed desktop session state UID mismatch")
        session_state.unlink()
    if xauthority.exists():
        raise RuntimeError("Managed Xauthority already exists; refusing to replace it")
    xauthority.touch(mode=0o600)
    atexit.register(xauthority.unlink, missing_ok=True)
    password = runtime / "secrets/viewer-password"
    auth = runtime / "secrets/vnc.passwd"
    if not auth.exists():
        value = secrets.token_urlsafe(8)[:8]
        password.write_text(value + "\n", encoding="utf-8")
        password.chmod(0o600)
        passwd_tool = shutil.which("tigervncpasswd") or shutil.which("vncpasswd")
        if not passwd_tool:
            raise RuntimeError("TigerVNC password utility is missing")
        result = subprocess.run([passwd_tool, "-f"], input=(value + "\n").encode(),
                                capture_output=True, check=True, timeout=10,
                                env=_child_env(metadata, {}))
        auth.write_bytes(result.stdout)
        auth.chmod(0o600)
    if auth.stat().st_uid != os.getuid() or auth.stat().st_mode & 0o077:
        raise RuntimeError("VNC authentication file is not private")
    subprocess.run(["xauth", "-f", str(xauthority)],
                   input=f"add {desktop['display']} MIT-MAGIC-COOKIE-1 {secrets.token_hex(16)}\n",
                   text=True, capture_output=True, check=True, timeout=10,
                   env=_child_env(metadata, {}))
    config = runtime / "desktop/config/xfce4/xfconf/xfce-perchannel-xml"
    config.mkdir(mode=0o700, parents=True, exist_ok=True)
    (config / "xfwm4.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><channel name="xfwm4" version="1.0">'
        '<property name="general" type="empty"><property name="use_compositing" '
        'type="bool" value="false"/></property></channel>\n', encoding="utf-8")
    env = _child_env(metadata, {"DISPLAY": desktop["display"], "XAUTHORITY": str(xauthority)})
    env.update({"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "XFCE", "DESKTOP_SESSION": "xfce",
                "XDG_CONFIG_HOME": str(runtime / "desktop/config"),
                "XDG_DATA_HOME": str(runtime / "desktop/data"),
                "XDG_CACHE_HOME": str(runtime / "desktop/cache")})
    server = shutil.which("Xtigervnc") or shutil.which("Xvnc")
    if not server:
        raise RuntimeError("TigerVNC X server is missing")
    children: list[subprocess.Popen] = []
    handles = []
    stopping = False

    def _stop(*_args: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        log = (runtime / "logs/xserver.log").open("ab")
        handles.append(log)
        children.append(subprocess.Popen(
            [server, desktop["display"], "-desktop", "ChatUp Computer Use", "-geometry", "1440x900",
             "-depth", "24", "-localhost=1", "-rfbport", str(desktop["vnc_port"]),
             "-SecurityTypes", "VncAuth", "-rfbauth", str(auth), "-auth", str(xauthority),
             "-nolisten", "tcp", "-AlwaysShared"],
            env=env, stdout=log, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and not stopping:
            if children[0].poll() is not None:
                raise RuntimeError("Managed X server exited during startup")
            result = subprocess.run(["xdpyinfo", "-display", desktop["display"]], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            if result.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Managed X server did not become ready")
        subprocess.run(["xset", "s", "off"], env=env, capture_output=True, timeout=5, check=False)
        subprocess.run(["xset", "-dpms"], env=env, capture_output=True, timeout=5, check=False)
        log = (runtime / "logs/xfce.log").open("ab")
        handles.append(log)
        children.append(subprocess.Popen(["dbus-run-session", "--", str(runtime / "venv/bin/python"),
                                          str(Path(__file__).resolve()), str(runtime / "metadata.json"),
                                          "desktop-session"],
                                         env=env, stdout=log, stderr=subprocess.STDOUT))
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("Managed desktop component exited")
            time.sleep(1)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                pass
        for handle in handles:
            handle.close()
        session_state.unlink(missing_ok=True)
        xauthority.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        raise RuntimeError("Expected metadata path and entrypoint mode")
    metadata = _read_metadata(Path(args.pop(0)))
    mode = args.pop(0)
    checked_target(metadata)
    if mode == "status":
        try:
            checked_connection(metadata)
            ready = True
        except RuntimeError:
            ready = False
        print(json.dumps({"target": metadata["target"], "desktop": metadata["desktop"],
                          "entrypoints": metadata["entrypoints"], "ready": ready}, sort_keys=True))
        return 0
    if mode == "desktop-supervisor":
        _start_desktop(metadata)
        return 0
    if mode == "desktop-session":
        _desktop_session(metadata)
        return 0
    if mode == "desktop":
        if metadata["desktop"]["ownership"] != "managed-new":
            raise RuntimeError("Attached desktop lifecycle belongs to its original owner")
        if len(args) != 1 or args[0] not in {"start", "stop", "status"}:
            raise RuntimeError("Expected desktop start, stop or status")
        subprocess.run(["systemctl", "--user", args[0], metadata["desktop"]["service"]],
                       check=True, timeout=35, env=_child_env(metadata, {}))
        return 0
    _run_client(metadata, mode, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"Computer Use: {exc}") from None
