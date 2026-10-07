"""Check current-user Windows Node PATH persistence without mutating a host."""
import os
import sys
from pathlib import Path

from chatup.setup.nodejs import _detect_nodejs_runtime_from_managed_windows_home, has_required_nodejs

if os.name != 'nt':
    raise SystemExit('Windows runner only')

runtime = _detect_nodejs_runtime_from_managed_windows_home()
assert has_required_nodejs(runtime=runtime), 'Managed Node runtime missing'
assert runtime['source'] == 'chatarch'

import winreg
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_READ) as key:
    raw, _ = winreg.QueryValueEx(key, 'Path')

root = Path(os.environ['CHATARCH_HOME']) / 'nodejs'
expected = [str(Path(runtime['node_bin']).parent), str(root / 'npm')]
entries = [part.rstrip('\\/').casefold() for part in str(raw).split(';')]
for value in expected:
    assert entries.count(value.rstrip('\\/').casefold()) == 1, 'Managed current-user PATH entry missing or duplicated'

from chatup.setup.nodejs import run_npm_command
result = run_npm_command(['prefix', '-g'])
assert result.returncode == 0
assert Path(result.stdout.strip()).resolve() == (root / 'npm').resolve(), 'npm global prefix escaped ChatArch home'
print('MANAGED_NODE_USER_PATH_AND_NPM_PREFIX_OK')
