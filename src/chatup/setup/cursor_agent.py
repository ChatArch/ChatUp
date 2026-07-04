from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import click

from chatup.interaction import (
    abort_if_force_without_tty,
    abort_if_missing_without_tty,
    resolve_interactive_mode,
)
from chatup.utils.custom_logger import setup_logger

INSTALL_URL = "https://cursor.com/install"
DEFAULT_AUTH_PATH = Path(".config/cursor/auth.json")
DEFAULT_CLI_CONFIG_PATH = Path(".cursor/cli-config.json")
logger = setup_logger("setup_cursor_agent")


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_cursor_agent", log_level=str(log_level).upper())
    return logger


def find_cursor_agent() -> str | None:
    for command in ("agent", "cursor-agent"):
        found = shutil.which(command)
        if found:
            return found
    for candidate in (
        Path.home() / ".local/bin/agent",
        Path.home() / ".local/bin/cursor-agent",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def install_cursor_agent_with_official_script() -> str:
    logger.info("Installing Cursor Agent with official installer")
    result = subprocess.run(
        ["bash", "-lc", f"curl -fsSL {shlex.quote(INSTALL_URL)} | bash"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        click.echo("Failed to install Cursor Agent.", err=True)
        if result.stdout:
            click.echo(result.stdout.strip(), err=True)
        raise click.Abort()
    agent_bin = find_cursor_agent()
    if not agent_bin:
        fallback = Path.home() / ".local/bin/agent"
        if fallback.exists():
            return str(fallback)
        raise click.ClickException("Cursor Agent installer completed but agent binary was not found.")
    return agent_bin


def _write_json_0600(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _load_json_file(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise click.ClickException(f"Failed to read JSON file: {path}") from exc
    if not isinstance(loaded, dict):
        raise click.ClickException(f"Expected JSON object in {path}")
    return loaded


def write_auth_tokens(auth_path: Path, *, access_token: str, refresh_token: str) -> list[str]:
    if not access_token or not refresh_token:
        raise click.ClickException("Cursor auth requires both accessToken and refreshToken.")
    old = {}
    if auth_path.exists():
        try:
            old = _load_json_file(auth_path)
        except click.ClickException:
            old = {}
    data = {"accessToken": access_token, "refreshToken": refresh_token}
    _write_json_0600(auth_path, data)
    changed = []
    for key, value in data.items():
        if old.get(key) != value:
            changed.append(key)
    logger.info(f"Patched Cursor Agent auth file: {auth_path}")
    return changed


def copy_auth_json(source: Path, target: Path) -> list[str]:
    data = _load_json_file(source)
    access_token = data.get("accessToken")
    refresh_token = data.get("refreshToken")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise click.ClickException("Cursor auth JSON must contain accessToken and refreshToken string fields.")
    return write_auth_tokens(
        target,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def copy_cli_config(source: Path, target: Path) -> list[str]:
    data = _load_json_file(source)
    old = None
    if target.exists():
        try:
            old = _load_json_file(target)
        except click.ClickException:
            old = None
    _write_json_0600(target, data)
    logger.info(f"Patched Cursor Agent CLI config file: {target}")
    return ["cli-config"] if old != data else []


def _parse_env_assignment(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    try:
        parts = shlex.split(raw_value, posix=True)
        value = parts[0] if parts else ""
    except ValueError:
        value = raw_value.strip().strip('"').strip("'")
    return key, value


def load_cursor_tokens_from_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        raise click.ClickException(f"Failed to read env file: {path}") from exc
    for line in lines:
        parsed = _parse_env_assignment(line)
        if parsed:
            key, value = parsed
            values[key] = value
    access_token = values.get("CURSOR_ACCESS_TOKEN") or values.get("CURSOR_AUTH_TOKEN")
    refresh_token = values.get("CURSOR_REFRESH_TOKEN")
    if not access_token or not refresh_token:
        raise click.ClickException(
            "Cursor env file must provide CURSOR_ACCESS_TOKEN (or CURSOR_AUTH_TOKEN) and CURSOR_REFRESH_TOKEN."
        )
    return {"accessToken": access_token, "refreshToken": refresh_token}


def write_auth_from_env_file(source: Path, target: Path) -> list[str]:
    tokens = load_cursor_tokens_from_env_file(source)
    return write_auth_tokens(
        target,
        access_token=tokens["accessToken"],
        refresh_token=tokens["refreshToken"],
    )


def bootstrap_with_api_key_env(agent_bin: str, api_key_env: str) -> None:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise click.ClickException(f"Environment variable {api_key_env} is not set.")
    env = os.environ.copy()
    env["CURSOR_API_KEY"] = api_key
    result = subprocess.run(
        [agent_bin, "models"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise click.ClickException("Cursor Agent API-key bootstrap failed.")


def verify_cursor_agent(agent_bin: str) -> str:
    result = subprocess.run(
        [agent_bin, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise click.ClickException("Cursor Agent binary is not callable.")
    return result.stdout.strip()


def setup_cursor_agent(
    auth_json=None,
    auth_env=None,
    cli_config=None,
    api_key_env=None,
    install_only=False,
    interactive=None,
    log_level="INFO",
):
    _configure_logger(log_level)
    usage = "Usage: chatup cursor-agent [--auth-json PATH] [--auth-env PATH] [--cli-config PATH] [--api-key-env NAME] [-i|-I]"
    has_inputs = bool(auth_json or auth_env or cli_config or api_key_env or install_only)
    interactive, can_prompt, force_interactive, _auto_interactive, _need_prompt = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=not has_inputs,
    )
    try:
        abort_if_force_without_tty(force_interactive, can_prompt, usage)
        abort_if_missing_without_tty(
            missing_required=not has_inputs,
            interactive=interactive,
            can_prompt=can_prompt,
            message="Missing Cursor Agent setup input and no TTY is available for interactive prompts.",
            usage=usage,
        )
    except click.Abort:
        logger.error("Cursor Agent setup cannot continue without input")
        raise

    agent_bin = find_cursor_agent()
    if not agent_bin:
        agent_bin = install_cursor_agent_with_official_script()

    version = verify_cursor_agent(agent_bin)
    if install_only:
        click.echo("Cursor Agent install completed.")
        click.echo(f"Agent: {agent_bin}")
        if version:
            click.echo(f"Version: {version}")
        return

    home = Path.home()
    auth_path = home / DEFAULT_AUTH_PATH
    cli_config_path = home / DEFAULT_CLI_CONFIG_PATH
    changed_auth: list[str] = []
    changed_config: list[str] = []

    if auth_json:
        changed_auth = copy_auth_json(Path(auth_json).expanduser(), auth_path)
    if auth_env:
        changed_auth = write_auth_from_env_file(Path(auth_env).expanduser(), auth_path)
    if cli_config:
        changed_config = copy_cli_config(Path(cli_config).expanduser(), cli_config_path)
    if api_key_env:
        bootstrap_with_api_key_env(agent_bin, api_key_env)

    click.echo("Cursor Agent setup completed.")
    click.echo(f"Agent: {agent_bin}")
    if version:
        click.echo(f"Version: {version}")
    if auth_json or auth_env:
        click.echo(f"Auth: {auth_path}")
    if cli_config:
        click.echo(f"Config: {cli_config_path}")
    if changed_auth:
        click.echo("Updated Cursor Agent secret keys: " + ", ".join(sorted(changed_auth)))
    if changed_config:
        click.echo("Updated Cursor Agent config keys: " + ", ".join(sorted(changed_config)))
