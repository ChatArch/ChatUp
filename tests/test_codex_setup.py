from __future__ import annotations

import json
import os

import click
import pytest


def _write_env(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}='{value}'" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _set_test_home(monkeypatch, home):
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def test_codex_env_profile_does_not_backfill_missing_key_from_active_or_process_env(
    tmp_path, monkeypatch
):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    _set_test_home(monkeypatch, home)
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
    _set_test_home(monkeypatch, home)
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
    if os.name != "nt":
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
    _set_test_home(monkeypatch, home)
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


def test_codex_env_profile_rejects_dotenv_interpolation_backfill(tmp_path, monkeypatch):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    _set_test_home(monkeypatch, home)
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
        openai_dir / "apple.env",
        {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            "OPENAI_API_BASE": "https://crs.example/openai/v1",
            "OPENAI_API_MODEL": "gpt-5.5",
        },
    )

    with pytest.raises(click.ClickException, match="unresolved variable reference"):
        codex_setup.setup_codex(env_ref="apple", interactive=False)

    assert not (home / ".codex" / "auth.json").exists()


def test_codex_env_profile_rejects_path_traversal_name(tmp_path, monkeypatch):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    other_dir = envs_dir / "Other"
    _set_test_home(monkeypatch, home)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_DIR", envs_dir)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_FILE", envs_dir / ".env")
    monkeypatch.setattr(codex_setup, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(
        codex_setup,
        "should_install_global_npm_package",
        lambda *args, **kwargs: False,
    )
    _write_env(
        other_dir / "secret.env",
        {
            "OPENAI_API_KEY": "other-key-should-not-be-read",
            "OPENAI_API_BASE": "https://other.example/v1",
            "OPENAI_API_MODEL": "other-model",
        },
    )

    with pytest.raises(click.ClickException, match="profile name"):
        codex_setup.setup_codex(env_ref="../Other/secret", interactive=False)

    assert not (home / ".codex" / "auth.json").exists()


def test_codex_env_profile_prompt_defaults_stay_inside_selected_profile(
    tmp_path, monkeypatch
):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    openai_dir = envs_dir / "OpenAI"
    codex_dir = home / ".codex"
    codex_dir.mkdir(parents=True)
    (codex_dir / "config.toml").write_text(
        'model_provider = "crs"\n'
        'model = "existing-model"\n\n'
        '[model_providers.crs]\n'
        'base_url = "https://existing.example/v1"\n',
        encoding="utf-8",
    )
    _set_test_home(monkeypatch, home)
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
    monkeypatch.setattr(
        codex_setup,
        "resolve_interactive_mode",
        lambda **kwargs: (True, True, True, False, True),
    )
    monkeypatch.setattr(codex_setup, "abort_if_force_without_tty", lambda *a, **k: None)
    monkeypatch.setattr(codex_setup, "abort_if_missing_without_tty", lambda *a, **k: None)
    monkeypatch.setattr(
        codex_setup,
        "resolve_install_only_mode",
        lambda **kwargs: (False, False),
    )
    monkeypatch.setattr(
        codex_setup,
        "prompt_sensitive_value",
        lambda _label, value, _masker: value,
    )

    prompt_candidates = []

    def fake_prompt_text_value(_label, *candidates, fallback=None):
        prompt_candidates.extend(candidates)
        for candidate in candidates:
            if candidate:
                return candidate
        return fallback

    monkeypatch.setattr(codex_setup, "prompt_text_value", fake_prompt_text_value)
    _write_env(
        openai_dir / ".env",
        {
            "OPENAI_API_BASE": "https://active.example/v1",
            "OPENAI_API_MODEL": "active-model",
        },
    )
    _write_env(
        openai_dir / "apple.env",
        {
            "OPENAI_API_KEY": "apple-key",
            "OPENAI_API_BASE": "https://apple.example/v1",
            "OPENAI_API_MODEL": "apple-model",
        },
    )

    codex_setup.setup_codex(env_ref="apple", interactive=True)

    assert "https://existing.example/v1" not in prompt_candidates
    assert "existing-model" not in prompt_candidates
    assert "https://process.example/v1" not in prompt_candidates
    assert "process-model" not in prompt_candidates
    assert "https://active.example/v1" not in prompt_candidates
    assert "active-model" not in prompt_candidates
    config_text = (codex_dir / "config.toml").read_text(encoding="utf-8")
    assert 'base_url = "https://apple.example/v1"' in config_text
    assert 'model = "apple-model"' in config_text


def test_codex_default_model_is_gpt_5_6_sol():
    import chatup.setup.codex as codex_setup

    assert codex_setup.DEFAULT_MODEL == "gpt-5.6-sol"


@pytest.fixture
def isolated_codex_runtime(tmp_path, monkeypatch):
    import chatup.setup.codex as codex_setup

    home = tmp_path / "home"
    envs_dir = tmp_path / "chatarch" / "envs"
    _set_test_home(monkeypatch, home)
    for key in ("OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_API_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_DIR", envs_dir)
    monkeypatch.setattr(codex_setup, "CHATARCH_ENV_FILE", envs_dir / ".env")
    monkeypatch.setattr(codex_setup, "ensure_nodejs_requirement", lambda **kwargs: None)
    monkeypatch.setattr(codex_setup, "should_install_global_npm_package", lambda *a, **k: False)
    return codex_setup, home, envs_dir


@pytest.mark.parametrize("named_profile", [False, True])
def test_codex_cli_writes_sol_when_no_model_is_selected(isolated_codex_runtime, monkeypatch, named_profile):
    from click.testing import CliRunner
    from chatup.cli import main

    _module, home, envs_dir = isolated_codex_runtime
    if named_profile:
        _write_env(envs_dir / "OpenAI" / "selected.env", {"OPENAI_API_KEY": "test-profile-key"})
        # Selecting a profile must not pull an unrelated process model.
        monkeypatch.setenv("OPENAI_API_MODEL", "outside-model")
        args = ["codex", "-e", "selected", "-I"]
    else:
        args = ["codex", "--api-key", "test-key", "-I"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    content = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.6-sol"' in content
    assert 'wire_api = "responses"' in content


@pytest.mark.parametrize("source", ["cli", "profile", "existing", "process", "active-profile"])
def test_codex_explicit_model_sources_still_override_fallback(isolated_codex_runtime, monkeypatch, source):
    module, home, envs_dir = isolated_codex_runtime
    kwargs = {"api_key": "test-key", "interactive": False}
    if source == "cli":
        kwargs["model"] = "gpt-5.5"
    elif source == "profile":
        _write_env(envs_dir / "OpenAI" / "selected.env", {"OPENAI_API_MODEL": "gpt-5.5"})
        kwargs["env_ref"] = "selected"
    elif source == "existing":
        config = home / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "gpt-5.5"\n', encoding="utf-8")
    elif source == "process":
        monkeypatch.setenv("OPENAI_API_MODEL", "gpt-5.5")
    else:
        _write_env(envs_dir / "OpenAI" / ".env", {"OPENAI_API_MODEL": "gpt-5.5"})
    module.setup_codex(**kwargs)
    assert 'model = "gpt-5.5"' in (home / ".codex" / "config.toml").read_text(encoding="utf-8")


def test_codex_interactive_model_fallback_is_sol(isolated_codex_runtime, monkeypatch):
    module, home, _envs_dir = isolated_codex_runtime
    monkeypatch.setattr(module, "resolve_interactive_mode", lambda **kwargs: (True, True, True, False, True))
    monkeypatch.setattr(module, "resolve_install_only_mode", lambda **kwargs: (False, False))
    monkeypatch.setattr(module, "prompt_sensitive_value", lambda _label, value, _mask: value)
    fallbacks = {}

    def prompt(label, *candidates, fallback=None):
        fallbacks[label] = fallback
        return next((value for value in candidates if value), fallback)

    monkeypatch.setattr(module, "prompt_text_value", prompt)
    module.setup_codex(api_key="test-key", interactive=True)
    assert fallbacks["default model (optional)"] == "gpt-5.6-sol"
    assert 'model = "gpt-5.6-sol"' in (home / ".codex" / "config.toml").read_text(encoding="utf-8")


def test_codex_help_names_the_fallback_model():
    from click.testing import CliRunner
    from chatup.cli import main

    result = CliRunner().invoke(main, ["codex", "--help"])
    assert result.exit_code == 0
    assert "gpt-5.6-sol" in result.output
