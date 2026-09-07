from __future__ import annotations

import ctypes.util
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click
from chatenv import get_paths

from chatup.utils.custom_logger import setup_logger
from chatup.utils.platforming import chmod_executable, chmod_private, executable_name, is_windows, require_systemd

logger = setup_logger("setup_mysql")

DEFAULT_MYSQL_VERSION = "8.4.6"
DEFAULT_MYSQL_PLATFORM = "linux-glibc2.28-x86_64"
DEFAULT_MYSQL_PORT = 3307
DEFAULT_MYSQL_BIND_ADDRESS = "127.0.0.1"
DEFAULT_MYSQL_INSTANCE = "default"
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class MysqlLayout:
    home: Path
    downloads: Path
    runtimes: Path
    runtime: Path
    current: Path
    instances: Path
    instance: Path
    data: Path
    run: Path
    logs: Path
    tmp: Path
    config: Path
    socket: Path
    pid: Path
    error_log: Path
    service: Path


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_mysql", log_level=str(log_level).upper())
    return logger


def default_chatdata_home() -> Path:
    return get_paths().home_dir / "chatdata"


def validate_safe_name(value: str, *, field: str) -> str:
    if not value or not SAFE_NAME_RE.fullmatch(value):
        raise click.ClickException(
            f"Invalid {field}: {value!r}. Use letters, numbers, dot, underscore, or dash."
        )
    return value


def quote_identifier(value: str) -> str:
    validate_safe_name(value, field="database name")
    return f"`{value.replace('`', '``')}`"


def mysql_layout(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
) -> MysqlLayout:
    validate_safe_name(name, field="instance name")
    validate_safe_name(version, field="version")
    root = (home or default_chatdata_home()).expanduser()
    instance = root / "instances" / "mysql" / name
    runtimes = root / "runtimes" / "mysql"
    return MysqlLayout(
        home=root,
        downloads=root / "downloads",
        runtimes=runtimes,
        runtime=runtimes / version,
        current=runtimes / "current",
        instances=root / "instances" / "mysql",
        instance=instance,
        data=instance / "data",
        run=instance / "run",
        logs=instance / "logs",
        tmp=instance / "tmp",
        config=instance / "my.cnf",
        socket=instance / "run" / "mysql.sock",
        pid=instance / "run" / "mysqld.pid",
        error_log=instance / "logs" / "error.log",
        service=Path("~/.config/systemd/user").expanduser()
        / f"chatdata-mysql-{name}.service",
    )


def detect_mysql_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux" and machine in {"x86_64", "amd64"}:
        return DEFAULT_MYSQL_PLATFORM
    if system == "windows" and machine in {"x86_64", "amd64"}:
        return "winx64"
    raise click.ClickException(f"Unsupported MySQL platform: {platform.system()} {platform.machine()}")


def _mysql_archive_suffix(platform_name: str) -> str:
    return ".zip" if platform_name == "winx64" else ".tar.xz"


def mysql_asset_urls(
    version: str = DEFAULT_MYSQL_VERSION, platform_name: str | None = None
) -> tuple[str, str]:
    platform_name = platform_name or detect_mysql_platform()
    filename = f"mysql-{version}-{platform_name}{_mysql_archive_suffix(platform_name)}"
    major_minor = version.rsplit(".", 1)[0]
    base = f"https://cdn.mysql.com/archives/mysql-{major_minor}/{filename}"
    return base, f"{base}.md5"


def _read_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _download_url(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _parse_md5(text: str) -> str:
    for token in text.replace("=", " ").split():
        lowered = token.strip().lower()
        if len(lowered) == 32 and all(ch in "0123456789abcdef" for ch in lowered):
            return lowered
    raise click.ClickException("Could not parse MySQL md5 checksum")


def verify_md5(path: Path, expected: str) -> str:
    actual = hashlib.md5(path.read_bytes()).hexdigest()  # nosec: MySQL publishes md5 sidecars.
    if actual.lower() != expected.lower():
        raise click.ClickException(f"Checksum mismatch for {path.name}")
    return actual


def _safe_member_path(root: Path, member_name: str) -> Path:
    candidate = (root / member_name).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise click.ClickException(f"Unsafe tar path: {member_name}")
    return candidate


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:xz") as tar:
        members = tar.getmembers()
        prefixes = {
            member.name.split("/", 1)[0]
            for member in members
            if member.name and not member.name.startswith("/")
        }
        strip_prefix = next(iter(prefixes)) if len(prefixes) == 1 else ""
        for member in members:
            if not member.name or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise click.ClickException(f"Unsafe tar member: {member.name}")
            relative = member.name
            if strip_prefix and relative == strip_prefix:
                continue
            if strip_prefix and relative.startswith(strip_prefix + "/"):
                relative = relative[len(strip_prefix) + 1 :]
            if not relative:
                continue
            target = _safe_member_path(destination, relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if member.issym() or member.islnk():
                link_target = Path(member.linkname)
                if link_target.is_absolute() or ".." in link_target.parts:
                    raise click.ClickException(
                        f"Unsafe tar link: {member.name} -> {member.linkname}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    target.unlink()
                try:
                    os.symlink(member.linkname, target)
                except OSError:
                    if not is_windows():
                        raise
                    continue
                continue
            if not member.isfile():
                raise click.ClickException(f"Unsupported tar member type: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise click.ClickException(f"Could not extract {member.name}")
            with source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            if not is_windows():
                target.chmod(member.mode & 0o777)


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        prefixes = {
            Path(member.filename.replace("\\", "/")).parts[0]
            for member in members
            if member.filename and not member.filename.startswith(("/", "\\"))
        }
        strip_prefix = next(iter(prefixes)) if len(prefixes) == 1 else ""
        for member in members:
            raw_name = member.filename.replace("\\", "/")
            if not raw_name or raw_name.startswith("/") or ".." in Path(raw_name).parts:
                raise click.ClickException(f"Unsafe zip member: {member.filename}")
            relative = raw_name
            if strip_prefix and relative == strip_prefix:
                continue
            if strip_prefix and relative.startswith(strip_prefix + "/"):
                relative = relative[len(strip_prefix) + 1 :]
            if not relative:
                continue
            target = _safe_member_path(destination, relative)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            chmod_executable(target) if target.suffix.lower() == ".exe" else None


def install_mysql(
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
    force: bool = False,
    platform_name: str | None = None,
) -> dict[str, Any]:
    layout = mysql_layout(version=version, home=home)
    mysqld = layout.runtime / "bin" / executable_name("mysqld")
    if mysqld.exists() and not force:
        return {"version": version, "runtime": str(layout.runtime), "binary": str(mysqld), "reused": True}

    platform_name = platform_name or detect_mysql_platform()
    url, md5_url = mysql_asset_urls(version, platform_name=platform_name)
    archive = layout.downloads / Path(url).name
    md5_path = layout.downloads / f"{archive.name}.md5"
    _download_url(url, archive)
    md5_text = _read_url(md5_url).decode("utf-8", "replace")
    md5_path.write_text(md5_text, encoding="utf-8")
    actual = verify_md5(archive, _parse_md5(md5_text))

    layout.runtimes.mkdir(parents=True, exist_ok=True)
    tmp = layout.runtimes / f".{version}.tmp-{int(time.time())}"
    if tmp.exists():
        shutil.rmtree(tmp)
    if _mysql_archive_suffix(platform_name) == ".zip":
        safe_extract_zip(archive, tmp)
    else:
        safe_extract_tar(archive, tmp)
    if layout.runtime.exists():
        if not force:
            shutil.rmtree(tmp)
            return {"version": version, "runtime": str(layout.runtime), "binary": str(mysqld), "reused": True}
        shutil.rmtree(layout.runtime)
    tmp.replace(layout.runtime)
    if layout.current.exists() or layout.current.is_symlink():
        layout.current.unlink()
    layout.current.symlink_to(layout.runtime, target_is_directory=True)
    version_output = subprocess.run(
        [str(mysqld), "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    return {
        "version": version,
        "runtime": str(layout.runtime),
        "binary": str(mysqld),
        "download": str(archive),
        "md5": actual,
        "reused": False,
        "version_output": version_output,
    }


def check_port_free(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def mysql_doctor(
    port: int = DEFAULT_MYSQL_PORT,
    bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
) -> dict[str, Any]:
    libs = {
        name: ctypes.util.find_library(name)
        for name in ["aio", "numa", "ssl", "crypto", "ncurses", "tinfo", "z", "stdc++"]
    }
    missing = [name for name, value in libs.items() if value is None]
    return {
        "platform": detect_mysql_platform(),
        "port": port,
        "port_free": check_port_free(bind_address, port),
        "libraries": libs,
        "missing_libraries": missing,
        "systemd_user": shutil.which("systemctl") is not None,
    }


def render_my_cnf(
    layout: MysqlLayout,
    runtime: Path,
    port: int = DEFAULT_MYSQL_PORT,
    bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
) -> str:
    if is_windows():
        return f"""[mysqld]
basedir={runtime}
datadir={layout.data}
pid-file={layout.pid}
log-error={layout.error_log}
tmpdir={layout.tmp}
port={port}
bind-address={bind_address}
mysqlx=0
skip_name_resolve=ON
character-set-server=utf8mb4
collation-server=utf8mb4_bin

[client]
host={bind_address}
port={port}
user=root
"""
    return f"""[mysqld]
basedir={runtime}
datadir={layout.data}
socket={layout.socket}
pid-file={layout.pid}
log-error={layout.error_log}
tmpdir={layout.tmp}
port={port}
bind-address={bind_address}
mysqlx=0
skip_name_resolve=ON
character-set-server=utf8mb4
collation-server=utf8mb4_bin

[client]
socket={layout.socket}
port={port}
user=root
"""


def init_instance(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
    port: int = DEFAULT_MYSQL_PORT,
    bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
    initialize: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    layout = mysql_layout(name=name, version=version, home=home)
    runtime = layout.runtime
    mysqld = runtime / "bin" / "mysqld"
    if not mysqld.exists():
        raise click.ClickException(f"MySQL runtime not installed: {mysqld}")
    if layout.data.exists() and any(layout.data.iterdir()):
        if not force:
            return {"name": name, "config": str(layout.config), "data": str(layout.data), "initialized": False, "reused": True}
        shutil.rmtree(layout.data)
    for child in [layout.data, layout.run, layout.logs, layout.tmp]:
        child.mkdir(parents=True, exist_ok=True)
    layout.config.write_text(
        render_my_cnf(layout, runtime, port=port, bind_address=bind_address),
        encoding="utf-8",
    )
    chmod_private(layout.config)
    initialized = False
    if initialize:
        subprocess.run(
            [str(mysqld), f"--defaults-file={layout.config}", "--initialize-insecure"],
            check=True,
        )
        initialized = True
    manifest = {
        "name": name,
        "version": version,
        "port": port,
        "bind_address": bind_address,
        "socket": str(layout.socket),
        "config": str(layout.config),
        "data": str(layout.data),
        "runtime": str(runtime),
    }
    (layout.instance / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {**manifest, "initialized": initialized, "reused": False}


def service_name(name: str = DEFAULT_MYSQL_INSTANCE) -> str:
    validate_safe_name(name, field="instance name")
    return f"chatdata-mysql-{name}.service"


def render_service(layout: MysqlLayout, runtime: Path, name: str = DEFAULT_MYSQL_INSTANCE) -> str:
    return f"""[Unit]
Description=ChatData MySQL instance {name}
After=network.target

[Service]
Type=simple
WorkingDirectory={layout.instance}
ExecStart={runtime / 'bin' / executable_name('mysqld')} --defaults-file={layout.config}
ExecStop={runtime / 'bin' / executable_name('mysqladmin')} --socket={layout.socket} shutdown
Restart=on-failure
RestartSec=5s
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""


def install_service(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
) -> dict[str, Any]:
    require_systemd("chatup mysql --service")
    layout = mysql_layout(name=name, version=version, home=home)
    runtime = layout.runtime
    layout.service.parent.mkdir(parents=True, exist_ok=True)
    layout.service.write_text(render_service(layout, runtime, name=name), encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True)
    subprocess.run(
        ["systemctl", "--user", "enable", service_name(name)],
        check=False,
        capture_output=True,
        text=True,
    )
    return {"name": name, "service": str(layout.service), "unit": service_name(name)}


def systemctl_user(name: str, action: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user", action, service_name(name)],
        check=False,
        capture_output=True,
        text=True,
    )


def client_command(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
    binary: str = "mysql",
    database: str | None = None,
    port: int = DEFAULT_MYSQL_PORT,
    host: str = DEFAULT_MYSQL_BIND_ADDRESS,
) -> list[str]:
    layout = mysql_layout(name=name, version=version, home=home)
    command = [str(layout.runtime / "bin" / executable_name(binary)), "-uroot"]
    if is_windows():
        command.extend(["-h", host, "-P", str(port)])
    else:
        command.append(f"--socket={layout.socket}")
    if database is not None:
        validate_safe_name(database, field="database name")
        command.append(f"--database={database}")
    return command


def ping(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
    port: int = DEFAULT_MYSQL_PORT,
    host: str = DEFAULT_MYSQL_BIND_ADDRESS,
) -> dict[str, Any]:
    layout = mysql_layout(name=name, version=version, home=home)
    command = [str(layout.runtime / "bin" / executable_name("mysqladmin")), "-uroot"]
    if is_windows():
        command.extend(["-h", host, "-P", str(port)])
    else:
        command.append(f"--socket={layout.socket}")
    command.append("ping")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return {"name": name, "ok": result.returncode == 0, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def query(
    sql: str,
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
    database: str | None = None,
) -> str:
    result = subprocess.run(
        [*client_command(name=name, version=version, home=home, database=database), "--batch", "--raw", "--execute", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def create_database(
    database: str,
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
) -> str:
    sql = f"CREATE DATABASE IF NOT EXISTS {quote_identifier(database)} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"
    return query(sql, name=name, version=version, home=home)


def export_layout(
    name: str = DEFAULT_MYSQL_INSTANCE,
    version: str = DEFAULT_MYSQL_VERSION,
    home: Path | None = None,
) -> dict[str, str]:
    layout = mysql_layout(name=name, version=version, home=home)
    return {key: str(value) for key, value in asdict(layout).items()}


def _raise_for_completed_process(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or f"{action} failed with exit code {result.returncode}").strip()
    raise click.ClickException(detail)


def setup_mysql(
    *,
    version: str = DEFAULT_MYSQL_VERSION,
    home: str | Path | None = None,
    name: str = DEFAULT_MYSQL_INSTANCE,
    port: int = DEFAULT_MYSQL_PORT,
    bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
    install: bool = True,
    init: bool = True,
    initialize: bool = True,
    service: bool = True,
    start: bool = False,
    smoke: bool = False,
    database: str | None = None,
    force: bool = False,
    log_level: str = "INFO",
) -> dict[str, Any]:
    _configure_logger(log_level)
    if smoke and not start:
        raise click.ClickException("--smoke requires --start; pass --no-smoke when using --no-start.")
    home_path = Path(home).expanduser() if home else None
    result: dict[str, Any] = {"layout": export_layout(name=name, version=version, home=home_path)}
    if install:
        result["install"] = install_mysql(version=version, home=home_path, force=force)
    if init:
        result["instance"] = init_instance(
            name=name,
            version=version,
            home=home_path,
            port=port,
            bind_address=bind_address,
            initialize=initialize,
            force=force,
        )
    if service:
        result["service"] = install_service(name=name, version=version, home=home_path)
    if start:
        require_systemd("chatup mysql --start")
        _raise_for_completed_process(systemctl_user(name, "start"), f"start {name}")
        result["start"] = {"unit": service_name(name), "started": True}
    if smoke:
        result["ping"] = ping(name=name, version=version, home=home_path)
        if not result["ping"].get("ok"):
            raise click.ClickException(str(result["ping"].get("stderr") or "MySQL ping failed"))
        result["query"] = query("SELECT VERSION();", name=name, version=version, home=home_path).strip()
    if database:
        if not start:
            raise click.ClickException("--database requires --start so ChatUp can create it safely.")
        create_database(database, name=name, version=version, home=home_path)
        result["database"] = database
    click.echo(f"MySQL layout: {result['layout']['instance']}")
    if "install" in result:
        click.echo(f"MySQL runtime: {result['install']['runtime']}")
    if "service" in result:
        click.echo(f"MySQL service: {result['service']['unit']}")
    if "start" in result:
        click.echo(f"MySQL started: {result['start']['unit']}")
    return result
