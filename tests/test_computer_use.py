"""Computer Use safety contracts, including preview and side entry target checks."""

from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from click.testing import CliRunner

from chatup.cli import main
from chatup.computer_use import apply_computer_use, plan_computer_use
from chatup.computer_use_entry import checked_connection


@pytest.fixture(autouse=True)
def _linux_runtime_contract(request):
    portable = {"test_command_is_real_top_level_surface",
                "test_unsupported_platform_is_rejected_only_on_invocation",
                "test_test_module_collects_without_unix_pwd"}
    if sys.platform != "linux" and request.function.__name__ not in portable:
        pytest.skip("Linux X11 runtime contract; portable CLI/import checks still run")


def _x11(tmp_path: Path, display: str = ":20") -> tuple[Path, Path]:
    xauth = tmp_path / "Xauthority"
    xauth.write_text("fixture")
    sockets = tmp_path / "sockets"
    sockets.mkdir()
    (sockets / f"X{display[1:]}").touch()
    return xauth, sockets


def _fake_live_x11(monkeypatch, module) -> None:
    class Probe:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def settimeout(self, _seconds):
            return None

        def connect(self, _path):
            return None

    monkeypatch.setattr(module.socket, "socket", lambda *_args: Probe())


def test_command_is_real_top_level_surface():
    assert "computer-use" in main.commands
    for flag in ("--sudo", "--dry-run", "--display", "--xauthority", "--state"):
        assert flag in CliRunner().invoke(main, ["computer-use", "--help"]).output
    assert "computer-use" in CliRunner().invoke(main, ["--tree"]).output
    assert "computer-use" in CliRunner().invoke(main, ["--tree-brief"]).output


def test_test_module_collects_without_unix_pwd(tmp_path):
    script = """import builtins, runpy, sys
import pytest, click.testing
import chatup.cli, chatup.computer_use, chatup.computer_use_entry
original = builtins.__import__
def without_pwd(name, *args, **kwargs):
    if name == 'pwd':
        raise ModuleNotFoundError('pwd is unavailable on this platform')
    return original(name, *args, **kwargs)
builtins.__import__ = without_pwd
runpy.run_path(sys.argv[1])
"""
    result = subprocess.run([sys.executable, "-c", script, str(Path(__file__).resolve())],
                            cwd=tmp_path, env=dict(os.environ), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_fresh_cli_preview_does_not_create_home_or_load_typed_secrets(tmp_path):
    source = Path(__file__).resolve().parents[1]
    env = {
        "HOME": str(tmp_path / "home"),
        "CHATARCH_HOME": str(tmp_path / "chatarch"),
        "TMPDIR": str(tmp_path),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "PYTHONPATH": str(source / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    code = (
        "from chatenv.fields import BaseEnvConfig; "
        "BaseEnvConfig.load_all = lambda *a, **k: (_ for _ in ()).throw(AssertionError('secret load')); "
        "import subprocess; subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(AssertionError('process start')); "
        "from chatup.cli import main; from click.testing import CliRunner; "
        "r = CliRunner().invoke(main, ['computer-use', '--sudo', '--dry-run']); "
        "print(r.output); raise SystemExit(r.exit_code)"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=source, env=env,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)["desktop"]["ownership"] == "managed-new"
    assert not (tmp_path / "home").exists()
    assert not (tmp_path / "chatarch").exists()


def test_unsupported_platform_is_rejected_only_on_invocation(monkeypatch):
    import chatup.computer_use as cu

    monkeypatch.setattr(cu.platform, "system", lambda: "Windows")
    assert CliRunner().invoke(main, ["--help"]).exit_code == 0
    assert CliRunner().invoke(main, ["--tree"]).exit_code == 0
    result = CliRunner().invoke(main, ["computer-use"])
    assert result.exit_code != 0
    assert "Debian/Ubuntu Linux x86_64 X11" in result.output


def test_preview_is_strictly_read_only_even_with_sudo_dry_run(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    monkeypatch.setattr(cu, "_x11_socket_dir", tmp_path / "missing-sockets")
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu, "_desktop_packages_missing", lambda: True)
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "managed"))
    monkeypatch.setattr(cu.subprocess, "run", lambda *a, **k: pytest.fail("preview ran a subprocess"))
    monkeypatch.setattr(cu.subprocess, "Popen", lambda *a, **k: pytest.fail("preview started a process"))
    for flags in ([], ["--sudo", "--dry-run"]):
        result = CliRunner().invoke(main, ["computer-use", *flags])
        assert result.exit_code == 0, result.output
        plan = json.loads(result.output)
        assert plan["target"]["uid"] == os.getuid()
        assert plan["desktop"]["ownership"] == "managed-new"
        assert "sudo apt-get install" in " ".join(plan["actions"])
        assert not (tmp_path / "managed").exists()


def test_ubuntu_focal_new_desktop_plan_uses_available_tigervnc_common(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    original_read_text = Path.read_text
    def focal_os_release(path, *args, **kwargs):
        if path == Path("/etc/os-release"):
            return 'ID=ubuntu\nVERSION_ID="20.04"\n'
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", focal_os_release)
    monkeypatch.setattr(cu, "_x11_socket_dir", tmp_path / "sockets")
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_desktop_packages_missing", lambda: True)
    monkeypatch.setattr(cu.subprocess, "run", lambda *a, **k: pytest.fail("planning ran a process"))
    monkeypatch.delenv("DISPLAY", raising=False)
    plan = cu.plan_computer_use(home=tmp_path / "managed")
    package_action = next(action for action in plan.actions if action.startswith("sudo apt-get install"))
    assert plan.target["distribution"] == "ubuntu"
    assert "tigervnc-common" in package_action.split()
    assert "tigervnc-tools" not in package_action.split()
    assert not (tmp_path / "managed").exists()


def test_explicit_same_user_desktop_is_attached_without_service_claim(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    plan = plan_computer_use(home=tmp_path / "managed", display=":20", xauthority=xauth)
    assert plan.desktop.ownership == "attached"
    assert plan.desktop.display == ":20"
    assert all("enable" not in action and "restart" not in action for action in plan.actions)
    assert plan.service_path is None


def test_state_selection_rejects_wrong_identity_and_stale_connection(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    state = tmp_path / "desktop.json"
    state.write_text(json.dumps({"uid": os.getuid() + 1, "hostname": socket.gethostname(), "DISPLAY": ":20", "XAUTHORITY": str(xauth)}))
    with pytest.raises(RuntimeError, match="UID"):
        plan_computer_use(home=tmp_path / "managed", state=state)
    state.write_text(json.dumps({"uid": os.getuid(), "hostname": "wrong-host", "DISPLAY": ":20", "XAUTHORITY": str(xauth)}))
    with pytest.raises(RuntimeError, match="host"):
        plan_computer_use(home=tmp_path / "managed", state=state)
    state.write_text(json.dumps({"uid": os.getuid(), "hostname": socket.gethostname(), "DISPLAY": ":20", "XAUTHORITY": str(xauth)}))
    (sockets / "X20").unlink()
    with pytest.raises(RuntimeError, match="stale|socket"):
        plan_computer_use(home=tmp_path / "managed", state=state)


def test_default_plan_discovers_same_user_managed_desktop_before_new_one(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    home = tmp_path / "managed"
    state = home / "computer-use/run/desktop.env.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"uid": os.getuid(), "DISPLAY": ":20", "XAUTHORITY": str(xauth)}))
    state.chmod(0o600)
    plan = plan_computer_use(home=home)
    assert plan.desktop.ownership == "attached"
    assert plan.desktop.state_source == state
    assert plan.service_path is None
    assert not any("Create private Xfce" in action for action in plan.actions)


def test_current_same_user_x11_session_is_reused_without_state_file(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setenv("DISPLAY", ":20")
    monkeypatch.setenv("XAUTHORITY", str(xauth))
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    plan = plan_computer_use(home=tmp_path / "managed")
    assert plan.desktop.ownership == "attached"
    assert plan.desktop.display == ":20"
    assert plan.service_path is None


def test_runtime_entry_refuses_wrong_target_and_never_falls_back(tmp_path, monkeypatch):
    import chatup.computer_use_entry as entry

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(entry, "X11_SOCKET_DIR", sockets)
    monkeypatch.setattr(entry.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, entry)
    metadata = {"target": {"hostname": "wrong-host", "uid": os.getuid()}, "desktop": {"display": ":20", "xauthority": str(xauth)}}
    with pytest.raises(RuntimeError, match="host"):
        checked_connection(metadata)
    metadata["target"]["hostname"] = socket.gethostname()
    assert checked_connection(metadata)["DISPLAY"] == ":20"
    (sockets / "X20").unlink()
    with pytest.raises(RuntimeError, match="stale|socket"):
        checked_connection(metadata)


def test_regular_file_is_not_an_x11_socket(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    _, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    assert cu._socket_exists(":20") is False


def test_apply_rechecks_plan_identity_before_any_mutation(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    monkeypatch.setattr(cu, "_x11_socket_dir", tmp_path / "sockets")
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    plan = plan_computer_use(home=tmp_path / "managed")
    monkeypatch.setattr(cu.socket, "gethostname", lambda: "changed-host")
    with pytest.raises(RuntimeError, match="target"):
        apply_computer_use(plan)
    assert not (tmp_path / "managed").exists()


def test_apply_attaches_without_touching_owner_service_and_reuses_own_entrypoints(tmp_path, monkeypatch):
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu.shutil, "which", lambda name: "/usr/bin/xterm" if name == "xterm" else None)
    monkeypatch.setattr(cu, "_verified_driver", lambda runtime: True)
    monkeypatch.setattr(cu, "_run", lambda *a, **k: pytest.fail("owner service was touched"))
    monkeypatch.setenv("OPENAI_API_KEY", "private-fixture")
    calls = []
    def fake_chrome(app, **kwargs):
        assert "OPENAI_API_KEY" not in os.environ
        calls.append((app, kwargs))
        return {"binary": sys.executable}

    monkeypatch.setattr(native_desktop, "setup_desktop_app", fake_chrome)
    plan = plan_computer_use(home=tmp_path / "managed", display=":20", xauthority=xauth)
    result = apply_computer_use(plan)
    assert calls == [("chrome", {"sudo": True})]
    assert result["desktop"]["ownership"] == "attached"
    assert "desktop" not in result["entrypoints"]
    metadata = Path(result["metadata"])
    assert metadata.stat().st_mode & 0o077 == 0
    assert all(Path(path).is_file() for path in result["entrypoints"].values())
    next_plan = plan_computer_use(home=tmp_path / "managed")
    assert next_plan.desktop.ownership == "installed-attached"
    assert apply_computer_use(next_plan)["metadata"] == str(metadata)
    assert len(calls) == 1


def test_apply_reuses_verified_legacy_dedicated_driver_without_pip(tmp_path, monkeypatch):
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu.shutil, "which", lambda name: "/usr/bin/xterm" if name == "xterm" else None)
    home = tmp_path / "managed"
    venv = home / "computer-use/venv"
    binary = venv / "bin/cua-driver"
    binary.parent.mkdir(parents=True)
    binary.write_text("fixture")
    binary.chmod(0o700)
    (venv / "bin/python").symlink_to(sys.executable)
    metadata = venv / "lib/python3.12/site-packages/cua_driver-0.36.0.dist-info/METADATA"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Name: cua-driver\nVersion: 0.36.0\n")
    monkeypatch.setattr(cu, "_run", lambda *a, **k: pytest.fail("pip or service was run"))
    monkeypatch.setattr(native_desktop, "setup_desktop_app", lambda app, **kwargs:
                        {"binary": sys.executable})
    plan = plan_computer_use(home=home, display=":20", xauthority=xauth)
    assert plan.driver_reused is True
    assert plan.driver_source == venv
    assert "Reuse verified" in " ".join(plan.actions)
    apply_computer_use(plan)
    assert (plan.runtime / "venv").is_symlink()
    assert (plan.runtime / "venv").resolve() == venv


def test_attached_desktop_without_xterm_plans_and_applies_only_terminal_prerequisite(tmp_path, monkeypatch):
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu.shutil, "which", lambda name: "/usr/bin/sudo" if name == "sudo" else None)
    monkeypatch.setattr(cu, "_verified_driver", lambda runtime: True)
    monkeypatch.setattr(native_desktop, "setup_desktop_app", lambda app, **kwargs:
                        {"binary": sys.executable})
    calls = []
    monkeypatch.setattr(cu, "_run", lambda argv, **kwargs: calls.append(argv))
    plan = plan_computer_use(home=tmp_path / "managed", display=":20", xauthority=xauth)
    assert any("sudo apt-get install -y --no-install-recommends xterm" in action for action in plan.actions)
    result = apply_computer_use(plan)
    assert result["desktop"]["ownership"] == "attached"
    assert calls == [["sudo", "apt-get", "install", "-y", "--no-install-recommends", "xterm"]]


def test_new_desktop_apply_writes_only_owned_user_service_and_entrypoints(tmp_path, monkeypatch):
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    os_home = tmp_path / "os-home"
    os_home.mkdir()
    monkeypatch.setenv("HOME", str(os_home))
    monkeypatch.setattr(cu, "_x11_socket_dir", tmp_path / "sockets")
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu, "_desktop_packages_missing", lambda: False)
    monkeypatch.setattr(cu, "_verified_driver", lambda runtime: True)
    monkeypatch.setattr(native_desktop, "setup_desktop_app", lambda app, **kwargs:
                        {"binary": sys.executable})
    calls = []
    monkeypatch.setattr(cu, "_run", lambda argv, **kwargs: calls.append(argv))
    plan = plan_computer_use(home=tmp_path / "managed")
    assert plan.desktop.ownership == "managed-new"
    result = apply_computer_use(plan)
    assert calls == [["systemctl", "--user", "daemon-reload"],
                     ["systemctl", "--user", "enable", "--now", plan.desktop.service]]
    assert plan.service_path.is_file()
    assert plan.service_path.stat().st_mode & 0o077 == 0
    assert "desktop-supervisor" in plan.service_path.read_text()
    unit = plan.service_path.read_text()
    assert "SendSIGKILL=no" in unit
    assert "TimeoutStopSec=30s" in unit
    assert "StartLimitIntervalSec=120s" in unit
    assert "StartLimitBurst=3" in unit
    assert "MemoryMax=2G" in unit
    assert "TasksMax=256" in unit
    assert "desktop" in result["entrypoints"]
    entry_source = (plan.runtime / "libexec/entry.py").read_text()
    assert '"-localhost=1"' in entry_source
    assert '"VncAuth"' in entry_source


def test_driver_entry_strips_provider_and_installer_environment(tmp_path, monkeypatch):
    import chatup.computer_use_entry as entry

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(entry, "X11_SOCKET_DIR", sockets)
    monkeypatch.setattr(entry.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, entry)
    runtime = tmp_path / "runtime"
    (runtime / "driver-home").mkdir(parents=True, mode=0o700)
    driver = runtime / "venv/bin/cua-driver"
    driver.parent.mkdir(parents=True)
    driver.write_text("fixture")
    driver.chmod(0o700)
    (runtime / "venv/bin/python").symlink_to(sys.executable)
    distribution = runtime / "venv/lib/python3.12/site-packages/cua_driver-0.36.0.dist-info"
    distribution.mkdir(parents=True)
    (distribution / "METADATA").write_text("Name: cua-driver\nVersion: 0.36.0\n")
    metadata = {"target": {"hostname": socket.gethostname(), "uid": os.getuid()},
                "desktop": {"display": ":20", "xauthority": str(xauth)},
                "runtime": {"home": str(runtime)}}
    monkeypatch.setenv("OPENAI_API_KEY", "private-fixture")
    monkeypatch.setenv("PIP_INDEX_URL", "private-fixture")
    monkeypatch.setattr(entry.os, "chdir", lambda path: None)
    launched = {}
    monkeypatch.setattr(entry.os, "execve", lambda binary, argv, env:
                        launched.update({"binary": binary, "argv": argv, "env": env}))
    entry._run_client(metadata, "mcp", [])
    assert launched["argv"][1:4] == ["mcp", "--direct", "--no-overlay"]
    assert launched["env"]["DISPLAY"] == ":20"
    assert launched["env"]["HOME"] == str(runtime / "driver-home")
    assert "OPENAI_API_KEY" not in launched["env"]
    assert "PIP_INDEX_URL" not in launched["env"]


def test_generated_mcp_entry_uses_prepared_private_driver_home_only(tmp_path, monkeypatch):
    import pwd
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
    monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, cu)
    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu, "_verified_driver", lambda runtime: True)
    monkeypatch.setattr(native_desktop, "setup_desktop_app", lambda app, **kwargs:
                        {"binary": sys.executable})
    plan = cu.plan_computer_use(home=tmp_path / "managed", display=":20", xauthority=xauth)
    cu.apply_computer_use(plan)
    driver_home = plan.runtime / "driver-home"
    assert driver_home.is_dir()
    assert driver_home.stat().st_mode & 0o077 == 0

    entry_path = plan.runtime / "libexec/entry.py"
    spec = importlib.util.spec_from_file_location("generated_computer_use_entry", entry_path)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    monkeypatch.setattr(entry, "checked_connection", lambda metadata: {"DISPLAY": ":20"})
    monkeypatch.setattr(entry, "_verified_driver", lambda runtime: True)
    monkeypatch.setattr(entry.os, "chdir", lambda path: None)
    launched = {}
    monkeypatch.setattr(entry.os, "execve", lambda binary, argv, env:
                        launched.update({"binary": binary, "argv": argv, "env": env}))
    metadata = json.loads((plan.runtime / "metadata.json").read_text())
    entry._run_client(metadata, "mcp", [])
    assert launched["env"]["HOME"] == str(driver_home)
    assert launched["env"]["CUA_DRIVER_HOME"] == str(plan.runtime / "driver")
    assert entry._child_env(metadata, {})["HOME"] == pwd.getpwuid(os.getuid()).pw_dir


def test_chrome_launcher_rejects_flags_after_url_without_launch(tmp_path, monkeypatch):
    import chatup.computer_use_entry as entry

    chrome = tmp_path / "chrome"
    chrome.write_text("fixture")
    metadata = {"runtime": {"home": str(tmp_path), "chrome": str(chrome)}}
    monkeypatch.setattr(entry, "checked_connection", lambda metadata: {})
    monkeypatch.setattr(entry.os, "execve", lambda *args: pytest.fail("Chrome launched"))
    with pytest.raises(RuntimeError, match="Chrome flags"):
        entry._run_client(metadata, "chrome", ["https://example.invalid", "--user-data-dir=/tmp/other"])


def _offline_recovery_plan(tmp_path, monkeypatch, *, attached=True, verified_driver=True):
    import chatup.computer_use as cu
    import chatup.setup.desktop as native_desktop

    monkeypatch.setattr(cu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cu.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(cu, "_linux_distribution", lambda: "ubuntu")
    monkeypatch.setattr(cu, "_desktop_packages_missing", lambda: False)
    monkeypatch.setattr(cu.shutil, "which", lambda name: "/usr/bin/xterm" if name == "xterm" else None)
    monkeypatch.setattr(native_desktop, "setup_desktop_app", lambda app, **kwargs:
                        {"binary": sys.executable})
    home = tmp_path / "managed"
    if attached:
        xauth, sockets = _x11(tmp_path)
        monkeypatch.setattr(cu, "_x11_socket_dir", sockets)
        monkeypatch.setattr(cu.stat, "S_ISSOCK", lambda mode: True)
        _fake_live_x11(monkeypatch, cu)
        options = {"display": ":20", "xauthority": xauth}
    else:
        monkeypatch.setattr(cu, "_x11_socket_dir", tmp_path / "no-sockets")
        options = {}
    if verified_driver:
        monkeypatch.setattr(cu, "_verified_driver", lambda runtime: True)
    return cu.plan_computer_use(home=home, **options), options


def test_failed_pip_resumes_only_marked_private_exact_runtime(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    plan, options = _offline_recovery_plan(tmp_path, monkeypatch, verified_driver=False)
    calls = []
    def fake_run(argv, **kwargs):
        calls.append(argv)
        venv = plan.runtime / "venv"
        if argv[1:3] == ["-m", "venv"]:
            (venv / "bin").mkdir(parents=True, mode=0o700)
            python = venv / "bin/python"
            python.write_text("fixture")
            python.chmod(0o700)
        elif argv[1:4] == ["-m", "pip", "install"]:
            if sum(call[1:4] == ["-m", "pip", "install"] for call in calls) == 1:
                raise subprocess.CalledProcessError(1, argv)
            driver = venv / "bin/cua-driver"
            driver.write_text("fixture")
            driver.chmod(0o700)
            dist = venv / "lib/python3.12/site-packages/cua_driver-0.36.0.dist-info"
            dist.mkdir(parents=True)
            (dist / "METADATA").write_text("Name: cua-driver\nVersion: 0.36.0\n")

    monkeypatch.setattr(cu, "_run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        cu.apply_computer_use(plan)
    assert (plan.runtime / "venv/bin/python").is_file()
    assert not (plan.runtime / "metadata.json").exists()
    retry = cu.plan_computer_use(home=plan.home, **options)
    result = cu.apply_computer_use(retry)
    assert Path(result["metadata"]).is_file()
    assert sum(call[1:3] == ["-m", "venv"] for call in calls) == 1
    assert sum(call[1:4] == ["-m", "pip", "install"] for call in calls) == 2


@pytest.mark.parametrize("unknown_kind", ["directory", "symlink"])
def test_unknown_venv_is_preserved_and_refused(tmp_path, monkeypatch, unknown_kind):
    import chatup.computer_use as cu

    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch, verified_driver=False)
    venv = plan.runtime / "venv"
    venv.parent.mkdir(parents=True)
    if unknown_kind == "directory":
        venv.mkdir()
        sentinel = venv / "keep"
    else:
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        venv.symlink_to(foreign, target_is_directory=True)
        sentinel = foreign / "keep"
    sentinel.write_text("preserve")
    monkeypatch.setattr(cu, "_run", lambda *a, **k: pytest.fail("unknown venv was operated on"))
    with pytest.raises(RuntimeError, match="venv|receipt|environment"):
        cu.apply_computer_use(plan)
    assert sentinel.read_text() == "preserve"
    assert venv.is_symlink() == (unknown_kind == "symlink")


@pytest.mark.parametrize("wrong_field", ["hostname", "uid", "runtime", "version"])
def test_other_target_venv_receipt_cannot_authorize_retry(tmp_path, monkeypatch, wrong_field):
    import chatup.computer_use as cu

    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch, verified_driver=False)
    venv = plan.runtime / "venv"
    venv.mkdir(parents=True, mode=0o700)
    sentinel = venv / "keep"
    sentinel.write_text("preserve")
    receipt = {"hostname": socket.gethostname(), "uid": os.getuid(),
               "runtime": str(plan.runtime), "version": cu.DRIVER_VERSION}
    receipt[wrong_field] = "another-target"
    marker = plan.runtime / "venv-install.json"
    marker.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    marker.chmod(0o600)
    monkeypatch.setattr(cu, "_run", lambda *a, **k: pytest.fail("foreign venv was operated on"))
    with pytest.raises(RuntimeError, match="receipt|artifact"):
        cu.apply_computer_use(plan)
    assert sentinel.read_text() == "preserve"


def test_failed_launcher_generation_retries_before_metadata_publication(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    plan, options = _offline_recovery_plan(tmp_path, monkeypatch)
    original_write = cu._write_owned
    failed = False
    def fail_once(path, content, *, mode):
        nonlocal failed
        if path.name == "chatup-computer-chrome" and not failed:
            failed = True
            raise OSError("injected launcher write failure")
        return original_write(path, content, mode=mode)

    monkeypatch.setattr(cu, "_write_owned", fail_once)
    with pytest.raises(OSError, match="injected launcher"):
        cu.apply_computer_use(plan)
    assert not (plan.runtime / "metadata.json").exists()
    retry = cu.plan_computer_use(home=plan.home, **options)
    result = cu.apply_computer_use(retry)
    assert retry.desktop.ownership == "attached"
    assert all(Path(path).is_file() for path in result["entrypoints"].values())


def test_missing_declared_entrypoint_is_repaired_before_installed_success(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch)
    result = cu.apply_computer_use(plan)
    missing = Path(result["entrypoints"]["chrome"])
    missing.unlink()
    retry = cu.plan_computer_use(home=plan.home)
    assert retry.desktop.ownership == "attached"
    repaired = cu.apply_computer_use(retry)
    assert Path(repaired["entrypoints"]["chrome"]).is_file()
    assert cu.plan_computer_use(home=plan.home).desktop.ownership == "installed-attached"


def test_missing_entrypoint_repair_preserves_selected_desktop_state(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    plan, options = _offline_recovery_plan(tmp_path, monkeypatch)
    state = tmp_path / "selected-desktop.json"
    state.write_text(json.dumps({"hostname": socket.gethostname(), "uid": os.getuid(),
                                 "DISPLAY": options["display"],
                                 "XAUTHORITY": str(options["xauthority"])}))
    state.chmod(0o600)
    selected = cu.plan_computer_use(home=plan.home, state=state)
    installed = cu.apply_computer_use(selected)
    metadata = Path(installed["metadata"])
    original_metadata = metadata.read_bytes()
    Path(installed["entrypoints"]["chrome"]).unlink()

    retry = cu.plan_computer_use(home=plan.home)
    repaired = cu.apply_computer_use(retry)

    assert Path(repaired["entrypoints"]["chrome"]).is_file()
    assert metadata.read_bytes() == original_metadata
    assert retry.desktop.state_source == state


def test_failed_owned_service_generation_retries_without_published_metadata(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    os_home = tmp_path / "os-home"
    os_home.mkdir()
    monkeypatch.setenv("HOME", str(os_home))
    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch, attached=False)
    commands = []
    monkeypatch.setattr(cu, "_run", lambda argv, **kwargs: commands.append(argv))
    original_write = cu._write_owned
    failed = False
    def fail_once(path, content, *, mode):
        nonlocal failed
        if path == plan.service_path and not failed:
            failed = True
            raise OSError("injected service write failure")
        return original_write(path, content, mode=mode)

    monkeypatch.setattr(cu, "_write_owned", fail_once)
    with pytest.raises(OSError, match="injected service"):
        cu.apply_computer_use(plan)
    assert not (plan.runtime / "metadata.json").exists()
    assert commands == []
    retry = cu.plan_computer_use(home=plan.home)
    assert retry.desktop.ownership == "managed-new"
    cu.apply_computer_use(retry)
    assert plan.service_path.is_file()
    assert (plan.runtime / "metadata.json").is_file()
    assert commands == [["systemctl", "--user", "daemon-reload"],
                        ["systemctl", "--user", "enable", "--now", plan.desktop.service]]


def test_missing_declared_owned_service_is_repaired_before_installed_success(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    os_home = tmp_path / "os-home"
    os_home.mkdir()
    monkeypatch.setenv("HOME", str(os_home))
    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch, attached=False)
    monkeypatch.setattr(cu, "_run", lambda argv, **kwargs: None)
    cu.apply_computer_use(plan)
    plan.service_path.unlink()
    retry = cu.plan_computer_use(home=plan.home)
    assert retry.desktop.ownership == "managed-new"
    cu.apply_computer_use(retry)
    assert plan.service_path.is_file()
    assert cu.plan_computer_use(home=plan.home).desktop.ownership == "managed-existing"


def test_failed_owned_service_activation_reloads_only_its_unit_on_retry(tmp_path, monkeypatch):
    import chatup.computer_use as cu

    os_home = tmp_path / "os-home"
    os_home.mkdir()
    monkeypatch.setenv("HOME", str(os_home))
    plan, _ = _offline_recovery_plan(tmp_path, monkeypatch, attached=False)
    commands = []
    state = {"fail_reload": True, "ready": False}
    monkeypatch.setattr(cu, "_socket_accepts_connection", lambda display: state["ready"])
    def fake_run(argv, **kwargs):
        commands.append(argv)
        if argv == ["systemctl", "--user", "daemon-reload"] and state["fail_reload"]:
            state["fail_reload"] = False
            raise OSError("injected daemon-reload failure")
        if argv in (["systemctl", "--user", "start", plan.desktop.service],
                    ["systemctl", "--user", "enable", "--now", plan.desktop.service]):
            state["ready"] = True

    monkeypatch.setattr(cu, "_run", fake_run)
    with pytest.raises(OSError, match="injected daemon-reload"):
        cu.apply_computer_use(plan)
    assert (plan.runtime / "metadata.json").is_file()
    retry = cu.plan_computer_use(home=plan.home)
    assert retry.desktop.ownership == "managed-existing"
    cu.apply_computer_use(retry)
    assert commands == [["systemctl", "--user", "daemon-reload"],
                        ["systemctl", "--user", "daemon-reload"],
                        ["systemctl", "--user", "enable", "--now", plan.desktop.service]]


def test_owned_desktop_entry_requires_current_private_session_state(tmp_path, monkeypatch):
    import chatup.computer_use_entry as entry

    xauth, sockets = _x11(tmp_path)
    monkeypatch.setattr(entry, "X11_SOCKET_DIR", sockets)
    monkeypatch.setattr(entry.stat, "S_ISSOCK", lambda mode: True)
    _fake_live_x11(monkeypatch, entry)
    runtime = tmp_path / "runtime"
    run = runtime / "run"
    run.mkdir(parents=True)
    metadata = {"target": {"hostname": socket.gethostname(), "uid": os.getuid()},
                "desktop": {"display": ":20", "xauthority": str(xauth), "ownership": "managed-new"},
                "runtime": {"home": str(runtime)}}
    with pytest.raises(RuntimeError, match="not ready"):
        checked_connection(metadata)
    session = run / "desktop-session.json"
    session.write_text(json.dumps({"hostname": socket.gethostname(), "uid": os.getuid(),
                                   "display": ":20", "dbus_address": "unix:path=/tmp/test-bus"}))
    session.chmod(0o600)
    assert checked_connection(metadata)["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/tmp/test-bus"
    session.write_text(json.dumps({"hostname": "wrong-host", "uid": os.getuid(),
                                   "display": ":20", "dbus_address": "unix:path=/tmp/test-bus"}))
    with pytest.raises(RuntimeError, match="target"):
        checked_connection(metadata)
