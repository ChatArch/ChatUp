from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path

import click

from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_crs")

DEFAULT_CRS_PACKAGE = "@chatarch/claude-relay-service@1.0.0"
DEFAULT_INSTALL_DIR = Path("~/.chatarch/crs/local")
DEFAULT_REDIS_PORT = 6379
DEFAULT_CRS_PORT = 12392


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_crs", log_level=str(log_level).upper())
    return logger


def run_command(args, *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout=600, capture=False):
    logger.debug("Running command: %s", " ".join(map(str, args)))
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
        timeout=timeout,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def ensure_redis_binary() -> None:
    if shutil.which("redis-server") and shutil.which("redis-cli"):
        return
    if shutil.which("brew") and os.name != "nt":
        click.echo("Redis binary not found; installing Redis component with Homebrew (no brew service).")
        run_command(["brew", "install", "redis"], timeout=900)
    if not shutil.which("redis-server") or not shutil.which("redis-cli"):
        raise click.ClickException(
            "redis-server/redis-cli are required. Install Redis or provide them on PATH."
        )


def wait_for_redis(redis_port: int, attempts: int = 30) -> None:
    for _ in range(attempts):
        result = subprocess.run(
            ["redis-cli", "-h", "127.0.0.1", "-p", str(redis_port), "ping"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.stdout.strip() == "PONG":
            return
        time.sleep(1)
    raise click.ClickException(f"Redis did not become ready on 127.0.0.1:{redis_port}")


def start_local_redis(install_dir: Path, redis_port: int) -> dict[str, str]:
    ensure_redis_binary()
    runtime_dir = install_dir / "redis-runtime"
    data_dir = install_dir / "redis-data"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    redis_conf = runtime_dir / "redis.conf"
    redis_pid = runtime_dir / "redis.pid"
    redis_log = runtime_dir / "redis.log"
    redis_conf.write_text(
        "\n".join(
            [
                "bind 127.0.0.1",
                f"port {redis_port}",
                "protected-mode yes",
                "daemonize yes",
                f"pidfile {redis_pid}",
                f"logfile {redis_log}",
                f"dir {data_dir}",
                "dbfilename dump.rdb",
                "appendonly yes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if redis_pid.exists():
        try:
            pid = int(redis_pid.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
        except (ValueError, ProcessLookupError, PermissionError):
            run_command(["redis-server", redis_conf], timeout=60)
    else:
        run_command(["redis-server", redis_conf], timeout=60)
    wait_for_redis(redis_port)
    return {"conf": str(redis_conf), "pid": str(redis_pid), "log": str(redis_log), "data": str(data_dir)}


def package_root(app_root: Path) -> Path:
    return app_root / "node_modules" / "@chatarch" / "claude-relay-service"


def write_secret_file(path: Path) -> dict[str, str]:
    if path.exists():
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        return values
    values = {
        "JWT_SECRET": secrets.token_hex(48),
        "ENCRYPTION_KEY": secrets.token_hex(16),
        "WEB_SESSION_SECRET": secrets.token_hex(32),
        "ADMIN_USERNAME": "crs_local_admin",
        "ADMIN_PASSWORD": secrets.token_urlsafe(18),
    }
    old_umask = os.umask(0o077)
    try:
        path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
        path.chmod(0o600)
    finally:
        os.umask(old_umask)
    return values


def write_env_file(crs_root: Path, *, port: int, redis_port: int, secrets_values: dict[str, str]) -> Path:
    env_path = crs_root / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NODE_ENV=development",
                "HOST=127.0.0.1",
                f"PORT={port}",
                "REDIS_HOST=127.0.0.1",
                f"REDIS_PORT={redis_port}",
                "REDIS_PASSWORD=",
                "REDIS_DB=0",
                f"JWT_SECRET={secrets_values['JWT_SECRET']}",
                f"ENCRYPTION_KEY={secrets_values['ENCRYPTION_KEY']}",
                f"WEB_SESSION_SECRET={secrets_values['WEB_SESSION_SECRET']}",
                "WEB_TITLE=ChatArch Local CRS",
                "WEB_DESCRIPTION=Local ChatArch CRS installed by ChatUp",
                "ENABLE_CORS=true",
                "LOG_LEVEL=info",
                "WEBHOOK_ENABLED=false",
                "USER_MANAGEMENT_ENABLED=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    env_path.chmod(0o600)
    return env_path


def smoke_crs(port: int) -> None:
    import urllib.error
    import urllib.request

    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(1)
    else:
        raise click.ClickException(f"CRS did not become healthy at {base}/health")

    for path, expected in [("/admin-next/", 200), ("/", 302)]:
        try:
            opener = urllib.request.build_opener(NoRedirectHandler)
            response = opener.open(f"{base}{path}", timeout=5)
            status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        if status != expected:
            raise click.ClickException(f"Unexpected status for {path}: expected {expected}, got {status}")


class NoRedirectHandler(__import__("urllib.request").request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def setup_crs(
    *,
    package: str = DEFAULT_CRS_PACKAGE,
    install_dir: str | Path = DEFAULT_INSTALL_DIR,
    redis_port: int = DEFAULT_REDIS_PORT,
    port: int = DEFAULT_CRS_PORT,
    start: bool = True,
    smoke: bool = True,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    usage = "Usage: chatup crs [--install-dir PATH] [--port PORT] [--redis-port PORT]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    install_path = Path(install_dir).expanduser().resolve()
    app_root = install_path / "app"
    install_path.mkdir(parents=True, exist_ok=True)
    app_root.mkdir(parents=True, exist_ok=True)

    redis_info = start_local_redis(install_path, redis_port)

    if not (app_root / "package.json").exists():
        run_command(["npm", "init", "-y"], cwd=app_root, timeout=120, capture=True)
    run_command(["npm", "install", package, "--registry", "https://registry.npmjs.org/", "--no-audit"], cwd=app_root)

    crs_root = package_root(app_root)
    if not crs_root.exists():
        raise click.ClickException(f"Installed CRS package root not found: {crs_root}")
    for subdir in ["logs", "data", "temp"]:
        (crs_root / subdir).mkdir(parents=True, exist_ok=True)
    config_path = crs_root / "config" / "config.js"
    if not config_path.exists():
        shutil.copyfile(crs_root / "config" / "config.example.js", config_path)

    secrets_path = install_path / ".local-secrets.env"
    secrets_values = write_secret_file(secrets_path)
    write_env_file(crs_root, port=port, redis_port=redis_port, secrets_values=secrets_values)

    setup_log = install_path / "setup.raw.log"
    env = os.environ.copy()
    env.update(
        {
            "ADMIN_USERNAME": secrets_values["ADMIN_USERNAME"],
            "ADMIN_PASSWORD": secrets_values["ADMIN_PASSWORD"],
        }
    )
    with setup_log.open("w", encoding="utf-8") as log_file:
        subprocess.run(
            ["npm", "run", "setup"],
            cwd=crs_root,
            env=env,
            check=True,
            timeout=180,
            text=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    setup_log.chmod(0o600)

    run_command(["npm", "run", "install:web"], cwd=crs_root)
    run_command(["npm", "run", "build:web"], cwd=crs_root)

    if start:
        run_command(["npm", "run", "service:start:daemon"], cwd=crs_root, timeout=120)
    if smoke:
        smoke_crs(port)

    result = {
        "status": "installed",
        "package": package,
        "install_dir": str(install_path),
        "app_root": str(app_root),
        "package_root": str(crs_root),
        "crs_url": f"http://127.0.0.1:{port}",
        "redis_url": f"redis://127.0.0.1:{redis_port}/0",
        "redis": redis_info,
        "secrets_file": str(secrets_path),
    }
    click.echo(f"CRS installed: {result['crs_url']}")
    click.echo(f"Install dir: {install_path}")
    click.echo(f"Secrets file: {secrets_path}")
    return result
