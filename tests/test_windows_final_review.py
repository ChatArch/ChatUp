"""User-facing regressions from the final Windows setup review."""
import os
import sys
from types import SimpleNamespace

import click
import pytest

from chatup.setup import nodejs
from chatup.utils import platforming


def managed_runtime():
    return nodejs._build_runtime(
        'managed/node.exe', 'managed/npm.cmd', 'v24.1.0', '11.0',
        'chatarch', npm_cli='managed/npm-cli.js',
    )


@pytest.mark.parametrize('already_installed', [False, True])
def test_direct_tool_requirement_persists_managed_windows_path(monkeypatch, already_installed):
    """Codex/OpenCode must work in a new terminal without a prior nodejs command."""
    runtime = managed_runtime()
    missing = nodejs._build_runtime('', '', '', '', 'path')
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime', lambda: runtime if already_installed else missing)
    monkeypatch.setattr(nodejs, '_bootstrap_windows_node_lts', lambda **kwargs: runtime)
    persisted = []
    monkeypatch.setattr(nodejs, 'ensure_windows_user_path', lambda value: persisted.append(value))

    assert nodejs.ensure_nodejs_requirement(interactive=False) == runtime
    assert persisted == [runtime]


def test_direct_tool_requirement_propagates_path_write_failure(monkeypatch):
    runtime = managed_runtime()
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime', lambda: runtime)
    def fail_persistence(value):
        raise click.ClickException('User PATH write failed')
    monkeypatch.setattr(nodejs, 'ensure_windows_user_path', fail_persistence)
    with pytest.raises(click.ClickException, match='User PATH write failed'):
        nodejs.ensure_nodejs_requirement(interactive=False)


@pytest.mark.parametrize('windows', [False, True])
def test_runtime_selection_prefers_complete_npm_over_newer_broken_node(monkeypatch, windows):
    broken = nodejs._build_runtime('new/node.exe', 'new/npm.cmd' if windows else '', 'v26.1.0', '', 'path')
    ready = managed_runtime()
    monkeypatch.setattr(platforming, 'WINDOWS', windows)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_path', lambda: broken)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_managed_windows_home', lambda: ready)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_nvm', lambda: nodejs._build_runtime('', '', '', '', 'nvm'))
    assert nodejs._detect_nodejs_runtime() == ready


def test_windows_path_persistence_preserves_existing_process_system_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setenv('CHATARCH_HOME', str(tmp_path / 'chatarch'))
    previous_process_path = str(tmp_path / 'python-bin') + os.pathsep + str(tmp_path / 'system-bin')
    monkeypatch.setenv('PATH', previous_process_path)
    runtime = nodejs._build_runtime(
        str(tmp_path / 'node' / 'node.exe'), str(tmp_path / 'node' / 'npm.cmd'),
        'v24.1.0', '11.0', 'chatarch', npm_cli=str(tmp_path / 'node' / 'npm-cli.js'),
    )
    stored = {'Path': str(tmp_path / 'unrelated-user-bin')}
    registry = SimpleNamespace(
        HKEY_CURRENT_USER=object(), KEY_READ=1, KEY_WRITE=2, REG_EXPAND_SZ=2,
        OpenKey=lambda *args: object(),
        QueryValueEx=lambda key, name: (stored[name], 2),
        SetValueEx=lambda key, name, zero, kind, value: stored.update({name: value}),
        CloseKey=lambda key: None,
    )
    monkeypatch.setitem(sys.modules, 'winreg', registry)
    nodejs.ensure_windows_user_path(runtime)
    assert str(tmp_path / 'python-bin') in os.environ['PATH'].split(os.pathsep)
    assert str(tmp_path / 'system-bin') in os.environ['PATH'].split(os.pathsep)
    assert str(tmp_path / 'unrelated-user-bin') in stored['Path'].split(';')
    assert str(tmp_path / 'system-bin') not in stored['Path'].split(';')


def test_native_ci_starts_with_codex_not_prior_nodejs_setup():
    from pathlib import Path
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
    job = workflow.split('windows-node-codex-smoke:', 1)[1]
    first_codex = job.index('chatup codex --api-key')
    first_nodejs = job.index('chatup nodejs -I')
    assert first_codex < first_nodejs, 'CI must exercise direct tool bootstrap before nodejs setup masks the missing PATH'
    assert 'RefreshEnvironmentPath' in job, 'Launchers must run after a fresh environment reload'
