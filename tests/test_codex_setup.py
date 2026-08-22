from __future__ import annotations

import json

import click
import pytest


def _write_env(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}='{value}'" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_codex_env_profile_does_not_backfill_missing_key_from_active_or_process_env(
    tmp_path, monkeypatch
):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "process-key-should-not-be-used")
    monkeypatch.setenv("OPENAI_API_BASE", "https://process.example/v1")
    monkeypatch.setenv("OPENAI_API_MODEL", "process-model")
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_DIR", envs_dir)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_FILE", envs_dir / ".env")
    monkeypatch.setattr(codex_setup, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        codex_setup,
        "should_install_global_npm_package",
        lambda *args, **kwargs: False,
    )

    _write_env(
        openai_dir / ".env",
        {
            "OPENAI_API_KEY": "active-key-should-not-be-used",
            "OPENAI_API_BASE": "https://active.example/v1",
            "OPENAI_API_MODEL": "active-model",
        },
    )
    _write_env(
        openai_dir / "apple.env",
        {
            "OPENAI_API_BASE": "https://crs.example/openai/v1",
            "OPENAI_API_MODEL": "gpt-5.5",
        },
    )

    with pytest.raises(click.Abort):
        codex_setup.setup_codex(env_ref="apple", interactive=False)

    auth_path = home / ".codex" / "auth.json"
    if auth_path.exists():
        auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
        assert auth_data.get("OPENAI_API_KEY") not in {
            "active-key-should-not-be-used",
            "process-key-should-not-be-used",
        }


def test_codex_env_profile_writes_exact_named_profile_values(tmp_path, monkeypatch):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "process-key-should-not-be-used")
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_DIR", envs_dir)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_FILE", envs_dir / ".env")
    monkeypatch.setattr(codex_setup, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        codex_setup,
        "should_install_global_npm_package",
        lambda *args, **kwargs: False,
    )

    _write_env(
        openai_dir / ".env",
        {
            "OPENAI_API_KEY": "active-key-should-not-be-used",
            "OPENAI_API_BASE": "https://active.example/v1",
            "OPENAI_API_MODEL": "active-model",
        },
    )
    _write_env(
        openai_dir / "apple.env",
        {
            "OPENAI_API_KEY": "apple-key",
            "OPENAI_API_BASE": "https://crs.example/openai/v1",
            "OPENAI_API_MODEL": "gpt-5.5",
        },
    )

    codex_setup.setup_codex(env_ref="apple", interactive=False)

    auth_path = home / ".codex" / "auth.json"
    auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert auth_data == {"OPENAI_API_KEY": "apple-key"}
    assert auth_path.stat().st_mode & 0o777 == 0o600

    config_text = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.5"' in config_text
    assert 'base_url = "https://crs.example/openai/v1"' in config_text
    assert "active-key-should-not-be-used" not in config_text
    assert "process-key-should-not-be-used" not in config_text


def test_codex_env_dotenv_ref_loads_active_openai_profile(tmp_path, monkeypatch):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "process-key-should-not-be-used")
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_DIR", envs_dir)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_FILE", envs_dir / ".env")
    monkeypatch.setattr(codex_setup, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        codex_setup,
        "should_install_global_npm_package",
        lambda *args, **kwargs: False,
    )
    _write_env(
        openai_dir / ".env",
        {
            "OPENAI_API_KEY": "active-key",
            "OPENAI_API_BASE": "https://active.example/v1",
            "OPENAI_API_MODEL": "gpt-5.5",
        },
    )

    codex_setup.setup_codex(env_ref=".env", interactive=False)

    auth_data = json.loads((home / ".codex" / "auth.json").read_text(encoding="utf-8"))
    assert auth_data == {"OPENAI_API_KEY": "active-key"}
    config_text = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.5"' in config_text
    assert 'base_url = "https://active.example/v1"' in config_text
    assert "process-key-should-not-be-used" not in config_text


def test_codex_default_model_matches_shared_openai_default():
    from chatenv.configs import OpenAIConfig
    import chatup.setup.codex as codex_setup

    assert codex_setup.DEFAULT_MODEL == OpenAIConfig.OPENAI_API_MODEL.default
