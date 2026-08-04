from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import subprocess
from typing import Any

import click
from chatenv.paths import get_paths
from chatenv.store import EnvStore

from chatup.config import CursorAgentConfig
from chatup.utils.custom_logger import setup_logger

DEFAULT_INSTALL_URL = "https://cursor.com/install"
CREDENTIAL_STORE_CHOICES = ("native", "file-wrapper")
CURSOR_ACCESS_TOKEN_KEY = "CURSOR_ACCESS_TOKEN"
CURSOR_REFRESH_TOKEN_KEY = "CURSOR_REFRESH_TOKEN"
CURSOR_CREDENTIAL_STORE_KEY = "CURSOR_CREDENTIAL_STORE"
WRAPPER_MARKER = "Managed by ChatUp cursor-agent setup"
logger = setup_logger("setup_cursor_agent")


def _configure_logger(log_level: str = "INFO"):
    global logger
    logger = setup_logger("setup_cursor_agent", log_level=str(log_level).upper())
    return logger


def _cursor_auth_path() -> Path:
    return Path.home() / ".config" / "cursor" / "auth.json"


def _cursor_cli_config_path() -> Path:
    return Path.home() / ".cursor" / "cli-config.json"


def _cursor_agent_state_path() -> Path:
    return Path.home() / ".cursor" / "agent-cli-state.json"


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o600)
    except PermissionError:
        logger.warning(f"Could not chmod private file: {path}")


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - ClickException carries detail
        raise click.ClickException(f"Invalid JSON file: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise click.ClickException(f"Expected JSON object in {path}")
    return data


def _validate_auth_json(path: Path) -> dict[str, Any]:
    data = _read_json_file(path)
    missing = [key for key in ("accessToken", "refreshToken") if not data.get(key)]
    if missing:
        raise click.ClickException(
            f"Cursor auth JSON missing required key(s): {', '.join(missing)}"
        )
    return data


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        values[key] = value
    return values


def _write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _chmod_private(path)


def _cursor_env_store() -> EnvStore:
    return EnvStore(get_paths().envs_dir)


def _auth_data_from_tokens(
    access_token: str | None,
    refresh_token: str | None,
    *,
    source_label: str,
) -> dict[str, str]:
    missing = [
        name
        for name, value in (
            (CURSOR_ACCESS_TOKEN_KEY, access_token),
            (CURSOR_REFRESH_TOKEN_KEY, refresh_token),
        )
        if not value
    ]
    if missing:
        raise click.ClickException(
            f"Cursor auth {source_label} missing required key(s): {', '.join(missing)}"
        )
    return {"accessToken": str(access_token), "refreshToken": str(refresh_token)}


def _load_auth_from_env_file(path: Path) -> dict[str, str]:
    values = _parse_env_file(path)
    return _auth_data_from_tokens(
        values.get(CURSOR_ACCESS_TOKEN_KEY),
        values.get(CURSOR_REFRESH_TOKEN_KEY),
        source_label=f"env file {path}",
    )


def _load_auth_from_profile(profile_name: str) -> tuple[dict[str, str], dict[str, str]]:
    values = _cursor_env_store().load_profile(CursorAgentConfig, profile_name)
    auth_data = _auth_data_from_tokens(
        values.get(CURSOR_ACCESS_TOKEN_KEY),
        values.get(CURSOR_REFRESH_TOKEN_KEY),
        source_label=f"ChatEnv profile {profile_name}",
    )
    return auth_data, values


def _save_auth_to_profile(
    profile_name: str,
    auth_data: dict[str, Any],
    *,
    credential_store: str,
) -> Path:
    store = _cursor_env_store()
    values = store.load_profile(CursorAgentConfig, profile_name)
    values[CURSOR_ACCESS_TOKEN_KEY] = str(auth_data["accessToken"])
    values[CURSOR_REFRESH_TOKEN_KEY] = str(auth_data["refreshToken"])
    values[CURSOR_CREDENTIAL_STORE_KEY] = credential_store
    return store.save_profile(CursorAgentConfig, profile_name, values)


def _copy_json_private(source: Path, target: Path) -> dict[str, Any]:
    data = _read_json_file(source)
    _write_json_private(target, data)
    return data


def _resolve_cursor_agent_binary() -> str | None:
    return shutil.which("cursor-agent") or shutil.which("agent")


def _managed_wrapper_official_target(entrypoint: Path) -> Path | None:
    if not entrypoint.exists() or entrypoint.is_symlink():
        return None
    try:
        text = entrypoint.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    if WRAPPER_MARKER not in text:
        return None
    for line in text.splitlines():
        if line.startswith("CHATUP_CURSOR_AGENT_OFFICIAL="):
            value = line.split("=", 1)[1]
            try:
                parts = shlex.split(value)
            except ValueError:
                return None
            if parts:
                return Path(parts[0])
    return None


def _resolve_official_cursor_agent_binary(binary: str) -> Path:
    entrypoint = Path(binary).expanduser()
    managed_target = _managed_wrapper_official_target(entrypoint)
    if managed_target:
        return managed_target
    try:
        return entrypoint.resolve(strict=True)
    except FileNotFoundError:
        return entrypoint


def _entrypoint_for(name: str) -> Path | None:
    found = shutil.which(name)
    if not found:
        return None
    return Path(found).expanduser()


def _write_file_credential_wrapper(entrypoint: Path, official_binary: Path, auth_path: Path) -> bool:
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    existing_target = None
    if entrypoint.exists() or entrypoint.is_symlink():
        if entrypoint.is_symlink():
            existing_target = entrypoint.resolve(strict=False)
            entrypoint.unlink()
        else:
            managed_target = _managed_wrapper_official_target(entrypoint)
            if not managed_target:
                raise click.ClickException(f"Refusing to overwrite non-ChatUp Cursor Agent entrypoint: {entrypoint}")
            existing_target = managed_target
    if existing_target and existing_target == entrypoint:
        raise click.ClickException(f"Refusing to wrap Cursor Agent entrypoint that resolves to itself: {entrypoint}")
    official = official_binary.expanduser()
    script = f'''#!/usr/bin/env bash
set -euo pipefail
# {WRAPPER_MARKER}.
# This wrapper does not store token values; it reads Cursor auth.json at runtime.
CHATUP_CURSOR_AGENT_OFFICIAL={shlex.quote(str(official))}
CHATUP_CURSOR_AGENT_AUTH_JSON="${{CURSOR_AGENT_AUTH_JSON:-{shlex.quote(str(auth_path))}}}"
export AGENT_CLI_CREDENTIAL_STORE="${{AGENT_CLI_CREDENTIAL_STORE:-file}}"
if [ -z "${{CURSOR_AUTH_TOKEN:-}}" ] && [ -r "$CHATUP_CURSOR_AGENT_AUTH_JSON" ]; then
  CHATUP_CURSOR_AGENT_TOKEN="$(python3 - "$CHATUP_CURSOR_AGENT_AUTH_JSON" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
print(data.get("accessToken", ""), end="")
PY
)"
  if [ -n "$CHATUP_CURSOR_AGENT_TOKEN" ]; then
    export CURSOR_AUTH_TOKEN="$CHATUP_CURSOR_AGENT_TOKEN"
  fi
  unset CHATUP_CURSOR_AGENT_TOKEN
fi
exec -a "$0" "$CHATUP_CURSOR_AGENT_OFFICIAL" "$@"
'''
    entrypoint.write_text(script, encoding="utf-8")
    entrypoint.chmod(0o755)
    return True


def _write_file_credential_wrappers(binary: str) -> list[str]:
    official = _resolve_official_cursor_agent_binary(binary)
    written: list[str] = []
    for name in ("cursor-agent", "agent"):
        entrypoint = _entrypoint_for(name)
        if not entrypoint:
            continue
        current_official = _resolve_official_cursor_agent_binary(str(entrypoint))
        if current_official != official:
            continue
        if _write_file_credential_wrapper(entrypoint, official, _cursor_auth_path()):
            written.append(str(entrypoint))
    return written


def _install_cursor_agent_if_needed(*, install_url: str = DEFAULT_INSTALL_URL) -> bool:
    if _resolve_cursor_agent_binary():
        return False
    script = subprocess.run(
        ["bash", "-lc", f"curl -fsSL {install_url!r} | bash"],
        text=True,
        capture_output=True,
        timeout=300,
    )
    if script.returncode != 0:
        detail = (script.stderr or script.stdout).strip()
        raise click.ClickException(f"Cursor Agent installer failed: {detail}")
    if not _resolve_cursor_agent_binary():
        raise click.ClickException("Cursor Agent installer finished but cursor-agent is still not on PATH")
    return True


def _command_summary(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=120,
        env=env,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    return {
        "command": cmd[0],
        "returncode": proc.returncode,
        "stdout_lines": len(stdout.splitlines()) if stdout else 0,
        "stderr_lines": len(stderr.splitlines()) if stderr else 0,
    }


def setup_cursor_agent(
    *,
    auth_json: str | Path | None = None,
    auth_env: str | Path | None = None,
    env_profile: str | None = None,
    save_profile: str | None = None,
    cli_config: str | Path | None = None,
    agent_state: str | Path | None = None,
    api_key_env: str | None = None,
    credential_store: str = "native",
    install_only: bool = False,
    verify: bool = True,
    interactive: bool | None = None,
    log_level: str = "INFO",
) -> dict[str, Any]:
    """Install/verify Cursor Agent and write safe local login/config files.

    Returned data is intentionally redacted: it reports file paths, booleans, modes,
    and command success metadata only, never token values.
    """

    _configure_logger(log_level)
    if credential_store not in CREDENTIAL_STORE_CHOICES:
        raise click.ClickException(
            f"Unsupported credential store: {credential_store}. Expected one of: {', '.join(CREDENTIAL_STORE_CHOICES)}"
        )
    result: dict[str, Any] = {
        "installed_binary": False,
        "binary": None,
        "auth_json_written": False,
        "cli_config_written": False,
        "agent_state_written": False,
        "env_profile_loaded": False,
        "profile_saved": None,
        "credential_store": None,
        "wrapper_written": False,
        "wrappers": [],
        "verification": None,
    }
    result["credential_store"] = credential_store

    installed = _install_cursor_agent_if_needed()
    result["installed_binary"] = installed
    result["binary"] = _resolve_cursor_agent_binary()

    if install_only:
        click.echo(f"Cursor Agent binary: {result['binary']}")
        return result

    auth_sources = [name for name, value in (("--auth-json", auth_json), ("--auth-env", auth_env), ("--env-profile", env_profile)) if value]
    if len(auth_sources) > 1:
        raise click.ClickException(f"Use only one auth source: {', '.join(auth_sources)}")

    auth_data: dict[str, Any] | None = None
    if auth_json:
        source = Path(auth_json).expanduser()
        auth_data = _validate_auth_json(source)
        _write_json_private(_cursor_auth_path(), auth_data)
        result["auth_json_written"] = True
    elif auth_env:
        source = Path(auth_env).expanduser()
        auth_data = _load_auth_from_env_file(source)
        _write_json_private(_cursor_auth_path(), auth_data)
        result["auth_json_written"] = True
    elif env_profile:
        auth_data, profile_values = _load_auth_from_profile(env_profile)
        profile_credential_store = profile_values.get(CURSOR_CREDENTIAL_STORE_KEY)
        if profile_credential_store and credential_store == "native":
            credential_store = profile_credential_store
            if credential_store not in CREDENTIAL_STORE_CHOICES:
                raise click.ClickException(
                    f"Unsupported credential store in ChatEnv profile {env_profile}: {credential_store}"
                )
            result["credential_store"] = credential_store
        _write_json_private(_cursor_auth_path(), auth_data)
        result["auth_json_written"] = True
        result["env_profile_loaded"] = True

    if save_profile:
        if auth_data is None:
            raise click.ClickException("--save-profile requires --auth-json, --auth-env, or --env-profile")
        profile_path = _save_auth_to_profile(save_profile, auth_data, credential_store=credential_store)
        result["profile_saved"] = str(profile_path)

    if cli_config:
        _copy_json_private(Path(cli_config).expanduser(), _cursor_cli_config_path())
        result["cli_config_written"] = True

    if agent_state:
        _copy_json_private(Path(agent_state).expanduser(), _cursor_agent_state_path())
        result["agent_state_written"] = True

    for path in (_cursor_auth_path(), _cursor_cli_config_path(), _cursor_agent_state_path()):
        if path.exists():
            _chmod_private(path)

    if credential_store == "file-wrapper":
        if not _cursor_auth_path().exists():
            raise click.ClickException("--credential-store file-wrapper requires Cursor auth.json")
        binary = result["binary"] or _resolve_cursor_agent_binary()
        if not binary:
            raise click.ClickException("cursor-agent is not available on PATH")
        wrappers = _write_file_credential_wrappers(str(binary))
        result["wrappers"] = wrappers
        result["wrapper_written"] = bool(wrappers)
        result["binary"] = _resolve_cursor_agent_binary()

    if verify:
        binary = _resolve_cursor_agent_binary()
        if not binary:
            raise click.ClickException("cursor-agent is not available on PATH")
        env = os.environ.copy()
        if api_key_env:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise click.ClickException(f"Environment variable is not set: {api_key_env}")
            env["CURSOR_API_KEY"] = api_key
        result["verification"] = _command_summary([binary, "--version"], env=env)

    click.echo("Cursor Agent setup complete")
    click.echo(f"  binary: {result['binary']}")
    click.echo(f"  auth_json_written: {result['auth_json_written']}")
    click.echo(f"  cli_config_written: {result['cli_config_written']}")
    click.echo(f"  agent_state_written: {result['agent_state_written']}")
    click.echo(f"  env_profile_loaded: {result['env_profile_loaded']}")
    click.echo(f"  profile_saved: {bool(result['profile_saved'])}")
    click.echo(f"  credential_store: {result['credential_store']}")
    click.echo(f"  wrapper_written: {result['wrapper_written']}")
    return result
