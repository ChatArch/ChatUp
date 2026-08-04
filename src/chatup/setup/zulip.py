from __future__ import annotations

import secrets
import shutil
import subprocess
from pathlib import Path

import click
from chatenv.paths import get_paths

from chatup.config import ZulipAdminConfig
from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.setup.service_credentials import (
    load_chatenv_values,
    require_values,
    write_private_env_file,
    write_secret_file,
)
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_zulip")

DEFAULT_HOME = get_paths().home_dir / "zulip"
DEFAULT_IMAGE = "ghcr.io/zulip/zulip-server:12.1-0"
DEFAULT_POSTGRES_IMAGE = "zulip/zulip-postgresql:14"
DEFAULT_EXTERNAL_HOST = "zulip.public.wzhecnu.cn"
DEFAULT_BIND_ADDRESS = "127.0.0.1"
DEFAULT_PORT = 3095

ADMIN_ENV_KEYS = (
    "ZULIP_ADMIN_USERNAME",
    "ZULIP_ADMIN_EMAIL",
    "ZULIP_ADMIN_PASSWORD",
)

SERVICE_SECRET_FILES = {
    "postgres_password": "zulip__postgres_password",
    "memcached_password": "zulip__memcached_password",
    "rabbitmq_password": "zulip__rabbitmq_password",
    "redis_password": "zulip__redis_password",
    "secret_key": "zulip__secret_key",
    "email_password": "zulip__email_password",
}


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_zulip", log_level=str(log_level).upper())
    return logger


def normalize_zulip_admin_values(values: dict[str, str]) -> dict[str, str]:
    normalized = values.copy()
    if not normalized.get("ZULIP_ADMIN_EMAIL") and normalized.get("ZULIP_ADMIN_MAIL"):
        normalized["ZULIP_ADMIN_EMAIL"] = normalized["ZULIP_ADMIN_MAIL"]
    return normalized


def ensure_directories(home: Path) -> dict[str, Path]:
    paths = {
        "home": home,
        "compose": home / "compose",
        "secrets": home / "secrets",
        "logs": home / "logs",
        "backups": home / "backups",
        "data": home / "data",
        "data_zulip": home / "data" / "zulip",
        "data_postgresql": home / "data" / "postgresql-14",
        "data_rabbitmq": home / "data" / "rabbitmq",
        "data_redis": home / "data" / "redis",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    paths["secrets"].chmod(0o700)
    return paths


def ensure_service_secrets(secrets_dir: Path) -> dict[str, Path]:
    written: dict[str, Path] = {}
    for file_name in SERVICE_SECRET_FILES:
        # Docker secrets should not require human-readable values; keep them token-like.
        written[file_name] = write_secret_file(secrets_dir / file_name, secrets.token_urlsafe(36))
    return written


def render_compose_yaml(
    *,
    paths: dict[str, Path],
    image: str,
    postgres_image: str,
    external_host: str,
    admin_email: str,
    bind_address: str,
    port: int,
) -> str:
    secrets_yaml = "\n".join(
        f"  {compose_name}:\n    file: {paths['secrets'] / file_name}"
        for file_name, compose_name in SERVICE_SECRET_FILES.items()
    )
    return f"""---
name: chatarch-zulip

secrets:
{secrets_yaml}

services:
  database:
    image: "{postgres_image}"
    restart: unless-stopped
    secrets:
      - zulip__postgres_password
    environment:
      POSTGRES_DB: "zulip"
      POSTGRES_USER: "zulip"
      POSTGRES_PASSWORD_FILE: /run/secrets/zulip__postgres_password
    volumes:
      - "{paths['data_postgresql']}:/var/lib/postgresql/data:rw"

  memcached:
    image: "memcached:alpine"
    restart: unless-stopped
    command:
      - "sh"
      - "-euc"
      - |
        echo 'mech_list: plain' > "$$SASL_CONF_PATH"
        echo "zulip@$$HOSTNAME:$$(cat $$MEMCACHED_PASSWORD_FILE)" > "$$MEMCACHED_SASL_PWDB"
        echo "zulip@localhost:$$(cat $$MEMCACHED_PASSWORD_FILE)" >> "$$MEMCACHED_SASL_PWDB"
        exec memcached -S
    secrets:
      - zulip__memcached_password
    environment:
      SASL_CONF_PATH: "/home/memcache/memcached.conf"
      MEMCACHED_SASL_PWDB: "/home/memcache/memcached-sasl-db"
      MEMCACHED_PASSWORD_FILE: /run/secrets/zulip__memcached_password

  rabbitmq:
    image: "rabbitmq:4.2"
    restart: unless-stopped
    command:
      - "sh"
      - "-euc"
      - |
        export RABBITMQ_DEFAULT_PASS="$$(cat $$RABBITMQ_PASSWORD_FILE)"
        echo "default_user = $$RABBITMQ_DEFAULT_USER" >> /etc/rabbitmq/rabbitmq.conf
        echo "default_pass = $$RABBITMQ_DEFAULT_PASS" >> /etc/rabbitmq/rabbitmq.conf
        exec docker-entrypoint.sh rabbitmq-server
    secrets:
      - zulip__rabbitmq_password
    environment:
      RABBITMQ_DEFAULT_USER: "zulip"
      RABBITMQ_PASSWORD_FILE: /run/secrets/zulip__rabbitmq_password
    volumes:
      - "{paths['data_rabbitmq']}:/var/lib/rabbitmq:rw"

  redis:
    image: "redis:alpine"
    restart: unless-stopped
    command:
      - "sh"
      - "-euc"
      - '/usr/local/bin/docker-entrypoint.sh --requirepass "$$(cat $$REDIS_PASSWORD_FILE)"'
    secrets:
      - zulip__redis_password
    environment:
      REDIS_PASSWORD_FILE: /run/secrets/zulip__redis_password
    volumes:
      - "{paths['data_redis']}:/data:rw"

  zulip:
    image: "{image}"
    restart: unless-stopped
    ports:
      - "{bind_address}:{port}:80"
    secrets:
      - zulip__postgres_password
      - zulip__memcached_password
      - zulip__rabbitmq_password
      - zulip__redis_password
      - zulip__secret_key
      - zulip__email_password
    environment:
      SETTING_EXTERNAL_HOST: "{external_host}"
      SETTING_ZULIP_ADMINISTRATOR: "{admin_email}"
      SETTING_REMOTE_POSTGRES_HOST: "database"
      SETTING_MEMCACHED_LOCATION: "memcached:11211"
      SETTING_RABBITMQ_HOST: "rabbitmq"
      SETTING_REDIS_HOST: "redis"
      TRUST_GATEWAY_IP: "True"
    volumes:
      - "{paths['data_zulip']}:/data:rw"
    ulimits:
      nofile:
        soft: 1000000
        hard: 1048576
    depends_on:
      - database
      - memcached
      - rabbitmq
      - redis
"""


def compose_command() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise click.ClickException("Docker Compose is required. Run `chatup docker` first.")


def run_compose(compose_file: Path, *args: str, timeout: int = 900) -> None:
    subprocess.run([*compose_command(), "-f", str(compose_file), *args], check=True, timeout=timeout)


def setup_zulip(
    *,
    home: str | Path = DEFAULT_HOME,
    image: str = DEFAULT_IMAGE,
    postgres_image: str = DEFAULT_POSTGRES_IMAGE,
    external_host: str = DEFAULT_EXTERNAL_HOST,
    bind_address: str = DEFAULT_BIND_ADDRESS,
    port: int = DEFAULT_PORT,
    env_ref: str | Path | None = None,
    env_profile: str | None = None,
    write_admin_env: bool = True,
    write_compose: bool = True,
    pull: bool = False,
    start: bool = False,
    force: bool = False,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    usage = "Usage: chatup zulip [--home PATH] [-e ENV|--env-profile PROFILE]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    home_path = Path(home).expanduser().resolve()
    paths = ensure_directories(home_path)
    ensure_service_secrets(paths["secrets"])

    values, source = load_chatenv_values(ZulipAdminConfig, env_ref=env_ref, env_profile=env_profile)
    values = normalize_zulip_admin_values(values)
    if write_admin_env or write_compose:
        require_values(values, ADMIN_ENV_KEYS, label="Zulip admin")

    admin_env = None
    if write_admin_env:
        admin_env = write_private_env_file(paths["secrets"] / "admin.env", values, ADMIN_ENV_KEYS)

    compose_file = paths["compose"] / "compose.yaml"
    if write_compose:
        if compose_file.exists() and not force:
            logger.info("Keeping existing Zulip compose file at %s", compose_file)
        else:
            compose_file.write_text(
                render_compose_yaml(
                    paths=paths,
                    image=image,
                    postgres_image=postgres_image,
                    external_host=external_host,
                    admin_email=values["ZULIP_ADMIN_EMAIL"],
                    bind_address=bind_address,
                    port=port,
                ),
                encoding="utf-8",
            )
            compose_file.chmod(0o640)

    if pull:
        run_compose(compose_file, "pull")
    if start:
        run_compose(compose_file, "up", "-d")

    result = {
        "home": str(home_path),
        "compose": str(compose_file),
        "admin_env": str(admin_env) if admin_env else None,
        "admin_source": source if write_admin_env else None,
        "url": f"http://{bind_address}:{port}",
        "external_host": external_host,
        "pulled": pull,
        "started": start,
    }
    click.echo(f"Zulip home: {home_path}")
    if write_admin_env:
        click.echo(f"Zulip admin env: {admin_env} (managed from ChatEnv; values hidden)")
    if write_compose:
        click.echo(f"Zulip compose: {compose_file}")
        click.echo(f"Zulip local URL: http://{bind_address}:{port}")
    return result
