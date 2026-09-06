from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click
from chatenv import get_paths

from chatup.utils.custom_logger import setup_logger
from chatup.utils.platforming import chmod_executable, chmod_private, executable_name, require_systemd

logger = setup_logger("setup_twikoo")

DEFAULT_TWIKOO_REPO = "twikoojs/twikoo"
DEFAULT_TWIKOO_VERSION = "1.7.15"
DEFAULT_TWIKOO_PORT = 8892
DEFAULT_TWIKOO_BIND_ADDRESS = "127.0.0.1"
DEFAULT_TWIKOO_INSTANCE = "chatblog"
TWIKOO_RUNTIME_SUPPORT_FILES = ("ip2region.db", "xhr-sync-worker.js")


@dataclass(frozen=True)
class TwikooService:
    name: str
    path: Path


@dataclass(frozen=True)
class TwikooLayout:
    home: Path
    downloads: Path
    runtime: Path
    runtime_binary: Path
    instance: Path
    instance_bin: Path
    instance_env_link: Path
    binary: Path
    env: Path
    data: Path
    logs: Path
    run: Path
    tmp: Path
    service: TwikooService


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_twikoo", log_level=str(log_level).upper())
    return logger


def validate_safe_name(value: str, *, field: str) -> str:
    if not value or any(ch in value for ch in ("/", "\\", "\x00")) or value in {".", ".."}:
        raise click.ClickException(
            f"Invalid {field}: {value!r}. Use an instance-safe name without path separators."
        )
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(ch not in allowed for ch in value):
        raise click.ClickException(
            f"Invalid {field}: {value!r}. Use letters, numbers, dot, underscore, or dash."
        )
    return value


def default_twikoo_home() -> Path:
    return get_paths().home_dir / "twikoo"


def service_name(name: str = DEFAULT_TWIKOO_INSTANCE) -> str:
    validate_safe_name(name, field="instance name")
    return f"chatarch-twikoo-{name}.service"


def service_file_path(name: str = DEFAULT_TWIKOO_INSTANCE) -> Path:
    return Path("~/.config/systemd/user").expanduser() / service_name(name)


def twikoo_layout(
    name: str = DEFAULT_TWIKOO_INSTANCE,
    version: str = DEFAULT_TWIKOO_VERSION,
    home: Path | None = None,
) -> TwikooLayout:
    validate_safe_name(name, field="instance name")
    validate_safe_name(version, field="version")
    root = (home or default_twikoo_home()).expanduser()
    runtime = root / "runtimes" / version
    instance = root / "instances" / name
    instance_bin = instance / "bin" / executable_name("twikoo")
    return TwikooLayout(
        home=root,
        downloads=root / "downloads",
        runtime=runtime,
        runtime_binary=runtime / executable_name("twikoo"),
        instance=instance,
        instance_bin=instance_bin,
        instance_env_link=instance / "bin" / ".env",
        binary=instance_bin,
        env=instance / "env" / "twikoo.env",
        data=instance / "data",
        logs=instance / "logs",
        run=instance / "run",
        tmp=instance / "tmp",
        service=TwikooService(name=service_name(name), path=service_file_path(name)),
    )


def _machine_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise click.ClickException(f"Unsupported Twikoo release architecture: {machine}")


def select_twikoo_asset_name() -> str:
    system = platform.system().lower()
    arch = _machine_arch()
    if system == "linux" and arch == "x64":
        return "twikoo-linux-x64"
    if system == "darwin" and arch in {"x64", "arm64"}:
        return f"twikoo-darwin-{arch}"
    if system == "windows" and arch == "x64":
        return "twikoo-win-x64.exe"
    raise click.ClickException(f"Unsupported Twikoo release platform: {platform.system()} {platform.machine()}")


def twikoo_release_asset_url(repo: str, version: str, asset_name: str) -> str:
    version = version.removeprefix("v")
    return f"https://github.com/{repo}/releases/download/{version}/{asset_name}"


def _download_url(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=180) as response, target.open("wb") as handle:
        if response.status != 200:
            raise click.ClickException(f"Failed to download Twikoo release asset: HTTP {response.status}")
        shutil.copyfileobj(response, handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_twikoo_binary(
    *,
    repo: str = DEFAULT_TWIKOO_REPO,
    version: str = DEFAULT_TWIKOO_VERSION,
    home: Path | None = None,
    force: bool = False,
    asset_name: str | None = None,
) -> dict[str, Any]:
    layout = twikoo_layout(version=version, home=home)
    if layout.runtime_binary.exists() and not force:
        return {
            "version": version,
            "binary": str(layout.runtime_binary),
            "sha256": _sha256(layout.runtime_binary),
            "reused": True,
        }

    selected_asset = asset_name or select_twikoo_asset_name()
    url = twikoo_release_asset_url(repo, version, selected_asset)
    layout.runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".chatup-twikoo-", dir=layout.runtime) as tmp:
        tmp_path = Path(tmp) / selected_asset
        _download_url(url, tmp_path)
        chmod_executable(tmp_path)
        tmp_path.replace(layout.runtime_binary)
    chmod_executable(layout.runtime_binary)
    return {
        "version": version,
        "binary": str(layout.runtime_binary),
        "asset": selected_asset,
        "sha256": _sha256(layout.runtime_binary),
        "reused": False,
    }


def render_env(
    layout: TwikooLayout,
    *,
    port: int = DEFAULT_TWIKOO_PORT,
    bind_address: str = DEFAULT_TWIKOO_BIND_ADDRESS,
) -> str:
    return f"""# Managed by ChatUp. Do not store secrets in this generated default env file.
TWIKOO_HOST={bind_address}
TWIKOO_PORT={port}
TWIKOO_DATA={layout.data}
TWIKOO_THROTTLE=250
TWIKOO_LOG_LEVEL=info
TWIKOO_LOCALHOST_ONLY=true
TWIKOO_SHUTDOWN_TIMEOUT=5000
"""


def render_service(layout: TwikooLayout, *, name: str = DEFAULT_TWIKOO_INSTANCE) -> str:
    return f"""[Unit]
Description=ChatUp Twikoo comment service ({name})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={layout.instance}
EnvironmentFile={layout.env}
ExecStart={layout.binary}
Restart=always
RestartSec=5
StandardOutput=append:{layout.logs}/twikoo.stdout.log
StandardError=append:{layout.logs}/twikoo.stderr.log

[Install]
WantedBy=default.target
"""


def _link_or_copy_binary(source: Path, target: Path, *, force: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if not force:
            return
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    chmod_executable(target)


def ensure_runtime_binary(layout: TwikooLayout) -> Path:
    """Return the canonical runtime binary, migrating an existing asset-named file if present."""

    if layout.runtime_binary.exists():
        return layout.runtime_binary
    try:
        asset_name = select_twikoo_asset_name()
    except click.ClickException:
        asset_name = ""
    if asset_name:
        candidate = layout.runtime / asset_name
        if candidate.exists():
            _link_or_copy_binary(candidate, layout.runtime_binary, force=False)
            return layout.runtime_binary
    raise click.ClickException(
        f"Twikoo runtime binary is missing at {layout.runtime_binary}; run without --no-install first."
    )


def _copy_support_files(runtime: Path, target_dir: Path, *, force: bool = False) -> list[str]:
    copied: list[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in TWIKOO_RUNTIME_SUPPORT_FILES:
        source = runtime / filename
        if not source.exists():
            continue
        target = target_dir / filename
        if target.exists() and not force:
            copied.append(filename)
            continue
        shutil.copy2(source, target)
        copied.append(filename)
    return copied


def init_instance(
    *,
    name: str = DEFAULT_TWIKOO_INSTANCE,
    version: str = DEFAULT_TWIKOO_VERSION,
    home: Path | None = None,
    port: int = DEFAULT_TWIKOO_PORT,
    bind_address: str = DEFAULT_TWIKOO_BIND_ADDRESS,
    force: bool = False,
) -> dict[str, Any]:
    layout = twikoo_layout(name=name, version=version, home=home)
    for directory in [layout.data, layout.logs, layout.run, layout.tmp, layout.env.parent, layout.instance_bin.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    runtime_binary = ensure_runtime_binary(layout)
    _link_or_copy_binary(runtime_binary, layout.instance_bin, force=force)
    support_files = _copy_support_files(layout.runtime, layout.instance_bin.parent, force=force)
    if not layout.env.exists() or force:
        layout.env.write_text(render_env(layout, port=port, bind_address=bind_address), encoding="utf-8")
        chmod_private(layout.env)
    if layout.instance_env_link.exists() or layout.instance_env_link.is_symlink():
        if force:
            layout.instance_env_link.unlink()
    if not layout.instance_env_link.exists() and not layout.instance_env_link.is_symlink():
        try:
            os.symlink(Path("../env/twikoo.env"), layout.instance_env_link)
        except OSError:
            shutil.copy2(layout.env, layout.instance_env_link)
    return {
        "instance": str(layout.instance),
        "binary": str(layout.instance_bin),
        "env": str(layout.env),
        "data": str(layout.data),
        "support_files": support_files,
    }


def install_service(
    *,
    name: str = DEFAULT_TWIKOO_INSTANCE,
    version: str = DEFAULT_TWIKOO_VERSION,
    home: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    require_systemd("chatup twikoo --service")
    layout = twikoo_layout(name=name, version=version, home=home)
    layout.service.path.parent.mkdir(parents=True, exist_ok=True)
    if not layout.service.path.exists() or force:
        layout.service.path.write_text(render_service(layout, name=name), encoding="utf-8")
    return {"unit": layout.service.name, "path": str(layout.service.path)}


def export_layout(
    *,
    name: str = DEFAULT_TWIKOO_INSTANCE,
    version: str = DEFAULT_TWIKOO_VERSION,
    home: Path | None = None,
) -> dict[str, Any]:
    layout = twikoo_layout(name=name, version=version, home=home)
    data = asdict(layout)
    data["service"] = {"name": layout.service.name, "path": str(layout.service.path)}
    for key, value in list(data.items()):
        if isinstance(value, Path):
            data[key] = str(value)
    return data


def _systemctl_user(*args: str) -> None:
    subprocess.run(["systemctl", "--user", *args], check=True)


def start_service(name: str = DEFAULT_TWIKOO_INSTANCE) -> None:
    unit = service_name(name)
    _systemctl_user("daemon-reload")
    _systemctl_user("enable", "--now", unit)


def smoke_twikoo(*, port: int = DEFAULT_TWIKOO_PORT, bind_address: str = DEFAULT_TWIKOO_BIND_ADDRESS) -> str:
    import json

    url = f"http://{bind_address}:{port}/"
    with urllib.request.urlopen(url, timeout=15) as response:
        body = response.read().decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Twikoo smoke did not return JSON: {body[:200]}") from exc
    if payload.get("code") != 100:
        raise click.ClickException(f"Twikoo smoke failed: {payload}")
    return body


def setup_twikoo(
    *,
    name: str = DEFAULT_TWIKOO_INSTANCE,
    version: str = DEFAULT_TWIKOO_VERSION,
    repo: str = DEFAULT_TWIKOO_REPO,
    home: Path | None = None,
    port: int = DEFAULT_TWIKOO_PORT,
    bind_address: str = DEFAULT_TWIKOO_BIND_ADDRESS,
    install: bool = True,
    init: bool = True,
    service: bool = True,
    start: bool = False,
    smoke: bool = False,
    force: bool = False,
    log_level: str = "INFO",
) -> dict[str, Any]:
    _configure_logger(log_level)
    validate_safe_name(name, field="instance name")
    if smoke and not start:
        raise click.ClickException("--smoke requires --start")
    result: dict[str, Any] = {"layout": export_layout(name=name, version=version, home=home)}
    if install:
        result["install"] = install_twikoo_binary(repo=repo, version=version, home=home, force=force)
    if init:
        result["init"] = init_instance(
            name=name,
            version=version,
            home=home,
            port=port,
            bind_address=bind_address,
            force=force,
        )
    if service:
        result["service"] = install_service(name=name, version=version, home=home, force=force)
    if start:
        require_systemd("chatup twikoo --start")
        start_service(name)
        result["started"] = service_name(name)
    if smoke:
        result["smoke"] = smoke_twikoo(port=port, bind_address=bind_address)
    return result
