"""Regressions reproduced during independent Windows checkpoint review."""
from pathlib import Path

import chatup.setup.codex as codex
import chatup.setup.nodejs as nodejs
from chatup.utils import platforming


def test_codex_patch_preserves_multiline_strings_and_commented_table_headers(tmp_path):
    original = '''notes = """Keep this text unchanged:
model = "inside-notes"
preferred_auth_method = "inside-notes"
"""
preferred_auth_method = "apikey"
[desktop] # preserve header comment
preferred_auth_method = "desktop-local-value"
model = "desktop-local-model"
'''
    path = tmp_path / 'config.toml'
    path.write_text(original, encoding='utf-8')
    codex._write_codex_config(path, model='gpt-5.6-terra', base_url='https://api.example.invalid/v1')
    fixed = path.read_text(encoding='utf-8')
    # These are user content/table members, not obsolete root settings.
    assert 'model = "inside-notes"' in fixed
    assert 'preferred_auth_method = "inside-notes"' in fixed
    assert 'preferred_auth_method = "desktop-local-value"' in fixed
    assert 'model = "desktop-local-model"' in fixed
    assert '[desktop] # preserve header comment' in fixed


def test_codex_patch_supports_existing_inline_provider_tables(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text('model_providers = {crs = {name = "kept", extra = "unchanged"}}\n', encoding='utf-8')
    codex._write_codex_config(path, model='gpt-5.6-terra', base_url='https://api.example.invalid/v1')
    import tomlkit
    config = tomlkit.parse(path.read_text())
    assert config['model_providers']['crs']['extra'] == 'unchanged'
    assert config['model_providers']['crs']['base_url'] == 'https://api.example.invalid/v1'


def test_native_ci_launcher_has_the_managed_node_on_parent_path():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
    job = workflow.split('windows-node-codex-smoke:', 1)[1]
    assert '$managedNodeDir' in job
    assert '$env:PATH = "$managedNodeDir' in job


def test_old_path_node_does_not_win_over_new_managed_runtime(monkeypatch):
    old = nodejs._build_runtime('old/node.exe', 'old/npm.cmd', 'v18.20.0', '10.0', 'path', npm_cli='old/npm-cli.js')
    new = nodejs._build_runtime('new/node.exe', 'new/npm.cmd', 'v24.1.0', '11.0', 'chatarch', npm_cli='new/npm-cli.js')
    monkeypatch.setattr(platforming, 'WINDOWS', True)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_path', lambda: old)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_managed_windows_home', lambda: new)
    monkeypatch.setattr(nodejs, '_detect_nodejs_runtime_from_nvm', lambda: nodejs._build_runtime('', '', '', '', 'nvm'))
    assert nodejs._detect_nodejs_runtime() == new
