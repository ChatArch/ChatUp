from pathlib import Path

import pytest
from click.testing import CliRunner

from chatup.cli import main
from chatup.setup import hermes as setup


@pytest.mark.parametrize("source", [None, "cli", "profile", "existing-config", "existing-env", "process", "active-profile"])
def test_hermes_fallback_and_existing_model_precedence(tmp_path, monkeypatch, source):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / ".chatarch"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    installer = tmp_path / "installer.sh"
    installer.write_text("# fixture only; never executed\n")
    monkeypatch.setattr(setup, "_resolve_installer", lambda *args: installer)
    monkeypatch.setattr(setup, "_hermes_installed", lambda path: True)
    system = {}
    typed = {}
    override = {}
    monkeypatch.setattr(setup, "split_config_sources", lambda *args: (system, typed))
    monkeypatch.setattr(setup, "_load_env_ref", lambda *args: override)
    args = ["hermes", "--hermes-home", str(home), "-I"]
    if source == "cli":
        args += ["--model", "chosen-model"]
    elif source == "profile":
        override["OPENAI_API_MODEL"] = "chosen-model"
    elif source == "existing-config":
        (home / "config.yaml").write_text('model:\n  default: "chosen-model"\n')
    elif source == "existing-env":
        (home / ".env").write_text("OPENAI_API_MODEL=chosen-model\n")
    elif source == "process":
        system["OPENAI_API_MODEL"] = "chosen-model"
    elif source == "active-profile":
        typed["OPENAI_API_MODEL"] = "chosen-model"
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    expected = "chosen-model" if source else "gpt-5.6-terra"
    assert f"default: '{expected}'" in (home / "config.yaml").read_text()
    assert f'OPENAI_API_MODEL={expected}' in (home / ".env").read_text()


def test_hermes_help_names_fallback_model():
    result = CliRunner().invoke(main, ["hermes", "--help"])
    assert result.exit_code == 0
    assert "gpt-5.6-terra" in result.output
