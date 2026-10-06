from pathlib import Path
import subprocess
import pytest
import click

from chatup.setup import hermes
from chatup.utils import platforming


def test_windows_hermes_path_probe_rejects_success_without_matching_target(monkeypatch, tmp_path):
    installer = tmp_path / 'install.ps1'
    installer.write_text('# fixture')
    home = tmp_path / 'hermes-data'
    calls = []
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(hermes, 'is_windows', lambda: True)
    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, '{"HermesHome":"C:\\other\\location","InstallDir":"C:\\other\\location\\hermes-agent"}', '')
    monkeypatch.setattr(hermes.subprocess, 'run', fake_run)
    with pytest.raises(click.ClickException, match='path'):
        hermes._run_installer(installer, home)
    assert len(calls) == 1


def test_windows_cursor_refuses_official_installer_when_existing_user_dir_would_be_deleted(monkeypatch, tmp_path):
    from chatup.setup import cursor_agent
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(cursor_agent, 'is_windows', lambda: True)
    monkeypatch.setattr(cursor_agent, '_resolve_cursor_agent_binary', lambda: None)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    existing = tmp_path / 'cursor-agent'
    existing.mkdir()
    (existing / 'user-state.json').write_text('{}')
    monkeypatch.setattr(cursor_agent.subprocess, 'run', lambda *args, **kwargs: pytest.fail('must not invoke destructive upstream installer'))
    with pytest.raises(click.ClickException, match='existing'):
        cursor_agent._install_cursor_agent_if_needed()
    assert (existing / 'user-state.json').read_text() == '{}'


def test_windows_cursor_installer_error_is_bounded_and_redacted(monkeypatch, tmp_path):
    from chatup.setup import cursor_agent
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(cursor_agent, 'is_windows', lambda: True)
    monkeypatch.setattr(cursor_agent, '_resolve_cursor_agent_binary', lambda: None)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, '', 'Token=not-a-real-secret-but-must-not-echo')
    monkeypatch.setattr(cursor_agent.subprocess, 'run', fake_run)
    with pytest.raises(click.ClickException) as exc:
        cursor_agent._install_cursor_agent_if_needed()
    assert 'Token=' not in str(exc.value)
