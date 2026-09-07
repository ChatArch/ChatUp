from __future__ import annotations

import subprocess
from pathlib import Path

import click
from chatenv.paths import get_paths

from chatup.config import DiscourseAdminConfig
from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.setup.service_credentials import (
    load_chatenv_values,
    require_values,
    write_private_env_file,
)
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_discourse")

DEFAULT_HOME = get_paths().home_dir / "discourse"
DEFAULT_REPO = "https://github.com/discourse/discourse_docker.git"
DEFAULT_HOSTNAME = "discourse.public.wzhecnu.cn"
DEFAULT_PORT = 3088

ADMIN_KEYS = (
    "DISCOURSE_ADMIN_USERNAME",
    "DISCOURSE_ADMIN_EMAIL",
    "DISCOURSE_ADMIN_PASSWORD",
)


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_discourse", log_level=str(log_level).upper())
    return logger


def run_command(args: list[str], *, cwd: Path | None = None, timeout: int = 600) -> None:
    subprocess.run([str(arg) for arg in args], cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def render_app_yml(*, hostname: str, port: int, shared_dir: Path, with_ai: bool) -> str:
    plugins = ["https://github.com/discourse/docker_manager.git"]
    if with_ai:
        plugins.append("https://github.com/discourse/discourse-ai.git")
    plugin_hooks = "\n".join(
        "\n".join(
            [
                "    - exec:",
                "        cd: $home/plugins",
                "        cmd:",
                f"          - git clone {url}",
            ]
        )
        for url in plugins
    )
    return f"""templates:
  - templates/postgres.template.yml
  - templates/redis.template.yml
  - templates/web.template.yml
  - templates/web.ratelimited.template.yml

expose:
  - \"127.0.0.1:{port}:80\"

params:
  db_default_text_search_config: \"pg_catalog.english\"

# Credentials and API/model secrets should be managed outside this file.
# Admin bootstrap values are written by ChatUp to ../secrets/admin.env.
env:
  LANG: en_US.UTF-8
  DISCOURSE_HOSTNAME: {hostname}
  DISCOURSE_DEVELOPER_EMAILS: ''
  DISCOURSE_SKIP_EMAIL_SETUP: 1

volumes:
  - volume:
      host: {shared_dir}
      guest: /shared
  - volume:
      host: {shared_dir}/log/var-log
      guest: /var/log

hooks:
  after_code:
{plugin_hooks}

run:
  - exec: echo \"Beginning of custom commands\"
  - exec: echo \"End of custom commands\"
"""


def ensure_directories(home: Path) -> dict[str, Path]:
    paths = {
        "home": home,
        "docker": home / "docker",
        "containers": home / "docker" / "containers",
        "secrets": home / "secrets",
        "logs": home / "logs",
        "backups": home / "backups",
        "shared": home / "shared" / "standalone",
        "shared_log": home / "shared" / "standalone" / "log" / "var-log",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    from chatup.utils.platforming import chmod_private_dir

    chmod_private_dir(paths["secrets"])
    return paths


def clone_or_update_discourse_docker(docker_dir: Path, repo: str) -> None:
    if (docker_dir / ".git").exists():
        run_command(["git", "fetch", "--all", "--prune"], cwd=docker_dir)
        run_command(["git", "pull", "--ff-only"], cwd=docker_dir)
        return
    if any(docker_dir.iterdir()):
        raise click.ClickException(f"Discourse docker dir is not empty and not a git repo: {docker_dir}")
    run_command(["git", "clone", repo, str(docker_dir)], timeout=900)


def setup_discourse(
    *,
    home: str | Path = DEFAULT_HOME,
    hostname: str = DEFAULT_HOSTNAME,
    port: int = DEFAULT_PORT,
    env_ref: str | Path | None = None,
    env_profile: str | None = None,
    write_admin_env: bool = True,
    write_app_yml: bool = True,
    clone: bool = False,
    repo: str = DEFAULT_REPO,
    with_ai: bool = True,
    force: bool = False,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    usage = "Usage: chatup discourse [--home PATH] [-e ENV|--env-profile PROFILE]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    home_path = Path(home).expanduser().resolve()
    paths = ensure_directories(home_path)

    values, source = load_chatenv_values(DiscourseAdminConfig, env_ref=env_ref, env_profile=env_profile)
    if write_admin_env:
        require_values(values, ADMIN_KEYS, label="Discourse admin")
        admin_env = write_private_env_file(paths["secrets"] / "admin.env", values, ADMIN_KEYS)
    else:
        admin_env = None

    app_yml = paths["containers"] / "app.yml"
    if write_app_yml:
        if app_yml.exists() and not force:
            logger.info("Keeping existing Discourse app.yml at %s", app_yml)
        else:
            app_yml.write_text(
                render_app_yml(hostname=hostname, port=port, shared_dir=paths["shared"], with_ai=with_ai),
                encoding="utf-8",
            )
            from chatup.utils.platforming import chmod_private

            chmod_private(app_yml)

    if clone:
        clone_or_update_discourse_docker(paths["docker"], repo)

    result = {
        "home": str(home_path),
        "docker_dir": str(paths["docker"]),
        "app_yml": str(app_yml),
        "admin_env": str(admin_env) if admin_env else None,
        "admin_source": source if write_admin_env else None,
        "hostname": hostname,
        "port": port,
        "cloned": clone,
    }
    click.echo(f"Discourse home: {home_path}")
    if write_admin_env:
        click.echo(f"Discourse admin env: {admin_env} (managed from ChatEnv; values hidden)")
    if write_app_yml:
        click.echo(f"Discourse app.yml: {app_yml}")
    if clone:
        click.echo(f"Discourse docker repo: {paths['docker']}")
    return result
