from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import click
from chatenv.fields import BaseEnvConfig
from chatenv.paths import get_paths
from chatenv.store import EnvStore


def parse_env_file(path: str | Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_chatenv_values(
    config_cls: type[BaseEnvConfig],
    *,
    env_ref: str | Path | None = None,
    env_profile: str | None = None,
) -> tuple[dict[str, str], str]:
    """Load service setup values without printing secrets.

    Precedence is current environment > explicit env file/profile values.
    The env_ref option mirrors Cursor Agent's `-e/--env`: an existing path is
    parsed as a dotenv-style file; otherwise it is treated as a ChatEnv profile.
    """

    values: dict[str, str] = {}
    source = "environment"
    store = EnvStore(get_paths().envs_dir)

    if env_ref:
        candidate = Path(env_ref).expanduser()
        if candidate.exists():
            values.update(parse_env_file(candidate))
            source = str(candidate)
        else:
            values.update(store.load_profile(config_cls, str(env_ref)))
            source = f"ChatEnv profile {env_ref}"

    if env_profile:
        values.update(store.load_profile(config_cls, env_profile))
        source = f"ChatEnv profile {env_profile}"

    for key in config_cls.get_fields():
        env_value = os.getenv(key)
        if env_value:
            values[key] = env_value
            source = "environment"
    return values, source


def require_values(values: dict[str, str], required: Iterable[str], *, label: str) -> None:
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise click.ClickException(
            f"Missing {label} ChatEnv value(s): {', '.join(missing)}. "
            "Set them in ChatEnv, pass --env-profile, or pass -e/--env pointing to an env file."
        )


def write_private_env_file(path: str | Path, values: dict[str, str], keys: Iterable[str]) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    old_umask = os.umask(0o077)
    try:
        target.write_text("".join(f"{key}={values.get(key, '')}\n" for key in keys), encoding="utf-8")
        target.chmod(0o600)
    finally:
        os.umask(old_umask)
    return target


def write_secret_file(path: str | Path, value: str) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target
    old_umask = os.umask(0o077)
    try:
        target.write_text(value, encoding="utf-8")
        target.chmod(0o600)
    finally:
        os.umask(old_umask)
    return target
