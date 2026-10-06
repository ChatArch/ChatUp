"""Windows-only, inert native adapter contract checks for hosted CI."""
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request

if os.name != 'nt':
    raise SystemExit('Windows runner only')

from chatup.setup import cursor_agent, frp, hermes

assert frp.get_system_arch() in ('amd64', 'arm64')
assert cursor_agent._resolve_command_or_user_bin('cursor-agent') is None or isinstance(cursor_agent._resolve_command_or_user_bin('cursor-agent'), Path)
assert hermes._cache_installer_path().suffix == '.ps1'
assert hermes.CHATARCH_HERMES_WINDOWS_INSTALLER_URL.startswith('https://raw.githubusercontent.com/ChatArch/hermes-agent/')

# Only inspect upstream path resolution. Never install or start Hermes in CI.
with tempfile.TemporaryDirectory(prefix='chatup-hermes-probe-') as directory:
    root = Path(directory)
    script = root / 'install.ps1'
    with urllib.request.urlopen(hermes.CHATARCH_HERMES_WINDOWS_INSTALLER_URL, timeout=30) as response:
        assert response.status == 200
        payload = response.read(2 * 1024 * 1024 + 1)
        assert len(payload) <= 2 * 1024 * 1024
    script.write_bytes(payload)
    env = dict(os.environ, HERMES_HOME=str(root / 'hermes'))
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script),
         '-NonInteractive', '-HermesHome', str(root / 'hermes'), '-InstallDir', str(root / 'hermes' / 'hermes-agent'), '-ShowResolvedPaths'],
        capture_output=True, text=True, timeout=45, env=env,
    )
    assert result.returncode == 0, result.stderr[-1000:]
    assert str(root / 'hermes').casefold() in result.stdout.casefold()
    assert not (root / 'hermes' / 'hermes-agent').exists()
print('WINDOWS_NATIVE_ADAPTER_CONTRACT_OK')
