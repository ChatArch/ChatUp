from __future__ import annotations

import hashlib
import json
import lzma
import os
import platform
import secrets
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import click
from chatenv import get_paths

from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_gitea")

DEFAULT_GITEA_REPO = "ChatArch/gitea"
DEFAULT_GITEA_VERSION = "latest"
DEFAULT_INSTALL_DIR = get_paths().home_dir / "chattea" / "bin"
DEFAULT_WORK_DIR = get_paths().home_dir / "chattea" / "gitea"
DEFAULT_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_LISTEN_ADDR = "127.0.0.1"
DEFAULT_HTTP_PORT = 3000
DEFAULT_SERVICE_NAME = "chattea-gitea.service"
DEFAULT_DATABASE_BACKEND = "sqlite3"
DEFAULT_DATABASE_NAME = "gitea"
SUPPORTED_DATABASE_BACKENDS = ("sqlite3", "mysql")
DEFAULT_BINARY_NAME = "gitea.exe" if os.name == "nt" else "gitea"


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_gitea", log_level=str(log_level).upper())
    return logger


def _machine_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    if machine in {"i386", "i686", "x86"}:
        return "386"
    if machine == "riscv64":
        return "riscv64"
    raise click.ClickException(f"Unsupported machine architecture for Gitea release asset: {machine}")


def normalize_release_version(version: str) -> str:
    return version.removeprefix("v")


def resolve_latest_gitea_version(repo: str = DEFAULT_GITEA_REPO) -> str:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise click.ClickException(f"Could not resolve latest Gitea release tag from {repo}")
    return normalize_release_version(tag)


def resolve_requested_version(version: str, repo: str = DEFAULT_GITEA_REPO) -> str:
    value = (version or DEFAULT_GITEA_VERSION).strip()
    if value.lower() == "latest":
        return resolve_latest_gitea_version(repo)
    return normalize_release_version(value)


def select_gitea_asset_name(version: str) -> str:
    system = platform.system().lower()
    arch = _machine_arch()
    if system == "darwin":
        return f"gitea-{version}-darwin-10.12-{arch}.xz"
    if system == "linux":
        return f"gitea-{version}-linux-{arch}.xz"
    if system == "windows":
        return f"gitea-{version}-windows-4.0-{arch}.exe.xz"
    if system == "freebsd":
        return f"gitea-{version}-freebsd14-{arch}.xz"
    raise click.ClickException(f"Unsupported operating system for Gitea release asset: {system}")


def gitea_release_asset_url(repo: str, version: str, asset_name: str) -> str:
    version = normalize_release_version(version)
    return f"https://github.com/{repo}/releases/download/v{version}/{asset_name}"


def verify_sha256(path: Path, checksum_path: Path) -> None:
    expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise click.ClickException(
            f"Checksum verification failed for {path.name}: expected {expected}, got {actual}"
        )


def download_release_asset(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=120) as response:
        if response.status != 200:
            raise click.ClickException(f"Failed to download Gitea release asset: HTTP {response.status}")
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def decompress_xz(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with lzma.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    destination.chmod(0o755)


def install_gitea_release_binary(
    *,
    repo: str,
    version: str,
    install_dir: Path,
    binary_name: str,
    force: bool,
) -> tuple[Path, str]:
    resolved_version = resolve_requested_version(version, repo)
    asset_name = select_gitea_asset_name(resolved_version)
    url = gitea_release_asset_url(repo, resolved_version, asset_name)
    target = install_dir / binary_name
    if target.exists() and not force:
        logger.info("Reusing existing Gitea binary at %s", target)
        return target, resolved_version

    install_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".chatup-gitea-", dir=install_dir) as tmp:
        archive = Path(tmp) / asset_name
        checksum = Path(tmp) / f"{asset_name}.sha256"
        unpacked = Path(tmp) / binary_name
        download_release_asset(url, archive)
        download_release_asset(f"{url}.sha256", checksum)
        verify_sha256(archive, checksum)
        decompress_xz(archive, unpacked)
        unpacked.replace(target)
    return target, resolved_version


def verify_gitea_binary(path: Path, version: str) -> str:
    result = subprocess.run(
        [str(path), "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise click.ClickException(f"Gitea binary verification failed: {output}")
    if f"version {version}" not in output:
        raise click.ClickException(
            f"Gitea binary version mismatch: expected {version}, got {output}"
        )
    return output


def generate_secret(size: int = 48) -> str:
    return secrets.token_urlsafe(size)


def _base_url_host(base_url: str) -> str:
    without_scheme = base_url.split("://", 1)[-1]
    host = without_scheme.split("/", 1)[0]
    return host.split(":", 1)[0]


def default_mysql_socket(instance: str = "default") -> Path:
    return get_paths().home_dir / "chatdata" / "instances" / "mysql" / instance / "run" / "mysql.sock"


def _password_from_env(env_name: str | None) -> str:
    if not env_name:
        return ""
    value = os.getenv(env_name)
    if not value:
        raise click.ClickException(f"Environment variable {env_name} is not set or is empty.")
    return value


def render_database_section(
    work_dir: Path,
    *,
    backend: str = DEFAULT_DATABASE_BACKEND,
    host: str | None = None,
    name: str = DEFAULT_DATABASE_NAME,
    user: str = "root",
    password: str = "",
    ssl_mode: str = "disable",
) -> str:
    if backend == "sqlite3":
        return f"""[database]
DB_TYPE = sqlite3
PATH = {work_dir}/data/gitea.db
LOG_SQL = false
"""
    if backend == "mysql":
        database_host = host or str(default_mysql_socket())
        return f"""[database]
DB_TYPE = mysql
HOST = {database_host}
NAME = {name}
USER = {user}
PASSWD = {password}
SSL_MODE = {ssl_mode}
LOG_SQL = false
"""
    raise click.ClickException(f"Unsupported Gitea database backend: {backend}")


def render_app_ini(
    *,
    work_dir: Path,
    run_user: str,
    base_url: str = DEFAULT_BASE_URL,
    listen_addr: str = DEFAULT_LISTEN_ADDR,
    http_port: int = DEFAULT_HTTP_PORT,
    database_backend: str = DEFAULT_DATABASE_BACKEND,
    database_host: str | None = None,
    database_name: str = DEFAULT_DATABASE_NAME,
    database_user: str = "root",
    database_password: str = "",
) -> str:
    normalized_url = base_url.rstrip("/") + "/"
    database_section = render_database_section(
        work_dir,
        backend=database_backend,
        host=database_host,
        name=database_name,
        user=database_user,
        password=database_password,
    ).rstrip()
    return f"""APP_NAME = Gitea
RUN_USER = {run_user}
RUN_MODE = prod
WORK_PATH = {work_dir}

[repository]
ROOT = {work_dir}/data/gitea-repositories
DEFAULT_BRANCH = main

[server]
APP_DATA_PATH = {work_dir}/data
DOMAIN = {_base_url_host(normalized_url)}
HTTP_ADDR = {listen_addr}
HTTP_PORT = {http_port}
ROOT_URL = {normalized_url}
DISABLE_SSH = true
LFS_START_SERVER = true

{database_section}

[session]
PROVIDER = file
PROVIDER_CONFIG = {work_dir}/data/sessions

[log]
MODE = console,file
LEVEL = Info
ROOT_PATH = {work_dir}/log

[security]
INSTALL_LOCK = true
SECRET_KEY = {generate_secret()}
INTERNAL_TOKEN = {generate_secret(64)}
PASSWORD_HASH_ALGO = pbkdf2

[oauth2]
JWT_SECRET = {generate_secret(32)}

[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = false
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false

[mailer]
ENABLED = false

[actions]
ENABLED = false
"""


def init_gitea_config(
    *,
    work_dir: Path,
    config_path: Path,
    binary: Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    listen_addr: str = DEFAULT_LISTEN_ADDR,
    http_port: int = DEFAULT_HTTP_PORT,
    database_backend: str = DEFAULT_DATABASE_BACKEND,
    database_host: str | None = None,
    database_name: str = DEFAULT_DATABASE_NAME,
    database_user: str = "root",
    database_password: str = "",
    force: bool = False,
    run_migrate: bool = True,
) -> Path:
    if database_backend not in SUPPORTED_DATABASE_BACKENDS:
        raise click.ClickException(f"Unsupported database backend: {database_backend}")
    if config_path.exists() and not force:
        return config_path
    for child in [config_path.parent, work_dir / "data", work_dir / "log"]:
        child.mkdir(parents=True, exist_ok=True)
    run_user = os.environ.get("USER") or "git"
    config_path.write_text(
        render_app_ini(
            work_dir=work_dir,
            run_user=run_user,
            base_url=base_url,
            listen_addr=listen_addr,
            http_port=http_port,
            database_backend=database_backend,
            database_host=database_host,
            database_name=database_name,
            database_user=database_user,
            database_password=database_password,
        ),
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    if binary and run_migrate:
        subprocess.run(
            [str(binary), "--config", str(config_path), "--work-path", str(work_dir), "migrate"],
            check=False,
        )
    return config_path


def service_file_path(service_name: str = DEFAULT_SERVICE_NAME) -> Path:
    return Path("~/.config/systemd/user").expanduser() / service_name


def _read_ini_value(config: Path, section: str, key: str) -> str | None:
    current_section: str | None = None
    for line in config.expanduser().read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
        if current_section != section:
            continue
        existing_key, sep, value = line.partition("=")
        if sep and existing_key.strip().upper() == key.upper():
            return value.strip()
    return None


def chatdata_mysql_service_dependency(config: Path) -> str | None:
    if (_read_ini_value(config, "database", "DB_TYPE") or "").lower() != "mysql":
        return None
    host = _read_ini_value(config, "database", "HOST") or ""
    parts = Path(host).parts
    for index, part in enumerate(parts[:-1]):
        if part == "mysql" and index > 0 and parts[index - 1] == "instances" and index + 1 < len(parts):
            instance = parts[index + 1]
            if instance:
                return f"chatdata-mysql-{instance}.service"
    return None


def write_user_service(
    *,
    binary: Path,
    config_path: Path,
    work_dir: Path,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> Path:
    path = service_file_path(service_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    dependency = chatdata_mysql_service_dependency(config_path)
    after_units = " ".join(["network.target", *([dependency] if dependency else [])])
    requires_line = f"Requires={dependency}\n" if dependency else ""
    content = f"""[Unit]
Description=ChatUp managed Gitea service
After={after_units}
{requires_line}
[Service]
Type=simple
WorkingDirectory={work_dir}
ExecStart={binary} web --config {config_path} --work-path {work_dir}
Restart=always
RestartSec=5s
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""
    path.write_text(content, encoding="utf-8")
    return path


def setup_gitea(
    version: str = DEFAULT_GITEA_VERSION,
    repo: str = DEFAULT_GITEA_REPO,
    install_dir: str | Path = DEFAULT_INSTALL_DIR,
    binary_name: str = DEFAULT_BINARY_NAME,
    force: bool = False,
    init: bool = False,
    service: bool = False,
    work_dir: str | Path = DEFAULT_WORK_DIR,
    config_path: str | Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    listen_addr: str = DEFAULT_LISTEN_ADDR,
    port: int = DEFAULT_HTTP_PORT,
    database_backend: str = DEFAULT_DATABASE_BACKEND,
    database_host: str | None = None,
    database_name: str = DEFAULT_DATABASE_NAME,
    database_user: str = "root",
    database_password_env: str | None = None,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    logger.info("Start Gitea setup")
    usage = "Usage: chatup gitea [--version VERSION] [--install-dir PATH] [--init] [--service] [-i|-I]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    install_path = Path(install_dir).expanduser().resolve()
    target, resolved_version = install_gitea_release_binary(
        repo=repo,
        version=version,
        install_dir=install_path,
        binary_name=binary_name,
        force=force,
    )
    version_output = verify_gitea_binary(target, resolved_version)
    result: dict[str, object] = {
        "status": "installed",
        "path": str(target),
        "version": resolved_version,
        "version_output": version_output,
    }

    work_path = Path(work_dir).expanduser().resolve()
    resolved_config = (
        Path(config_path).expanduser().resolve()
        if config_path
        else work_path / "custom" / "conf" / "app.ini"
    )
    if init:
        generated_config = init_gitea_config(
            work_dir=work_path,
            config_path=resolved_config,
            binary=target,
            base_url=base_url,
            listen_addr=listen_addr,
            http_port=port,
            database_backend=database_backend,
            database_host=database_host,
            database_name=database_name,
            database_user=database_user,
            database_password=_password_from_env(database_password_env),
            force=force,
        )
        result["config"] = str(generated_config)
        result["work_dir"] = str(work_path)
    if service:
        if not init and not resolved_config.exists():
            raise click.ClickException("--service requires --init or an existing --config-path.")
        service_file = write_user_service(
            binary=target,
            config_path=resolved_config,
            work_dir=work_path,
        )
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True)
        result["service"] = str(service_file)

    click.echo(f"Gitea installed: {target}")
    click.echo(version_output)
    if "config" in result:
        click.echo(f"Gitea config: {result['config']}")
    if "service" in result:
        click.echo(f"Gitea service: {result['service']}")
    logger.info("Gitea setup completed")
    return result
