import base64
import importlib
import json
import subprocess

import pytest
from click.testing import CliRunner

from chatup.cli import main


@pytest.fixture
def desktop(monkeypatch, tmp_path):
    module = importlib.import_module("chatup.setup.desktop")
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    for variable in ("LOCALAPPDATA", "PROGRAMW6432", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        monkeypatch.setenv(variable, str(tmp_path / variable))
    return module


def test_chrome_preview_has_no_side_effects(desktop, monkeypatch):
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("process in dry run"))
    monkeypatch.setattr(desktop, "_cache_dir", lambda: pytest.fail("write in dry run"))
    result = CliRunner().invoke(main, ["chrome", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Google.Chrome.EXE" in result.output
    assert "--scope user" in result.output
    assert "--ignore-security-hash" not in result.output


@pytest.mark.parametrize("status,publisher,product,version,original", [
    ("HashMismatch", "Google LLC", "Google Chrome", "154.0.0.1", "chrome.exe"),
    ("Valid", "Not Google LLC", "Google Chrome", "154.0.0.1", "chrome.exe"),
    ("Valid", "Google LLC", "Chromium", "154.0.0.1", "chrome.exe"),
    ("Valid", "Google LLC", "Google Chrome", "", "chrome.exe"),
    ("Valid", "Google LLC", "Google Chrome", 154, "chrome.exe"),
    ("Valid", "Google LLC", "Google Chrome", "154.0.0.1", "other.exe"),
])
def test_invalid_binary_rejected(desktop, monkeypatch, tmp_path, status, publisher, product, version, original):
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "powershell.exe")
    payload = dict(status=status, publisher=publisher, product=product, version=version, original=original)
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: subprocess.CompletedProcess([], 0, json.dumps(payload), ""))
    with pytest.raises(RuntimeError):
        desktop._google_signed_file(tmp_path / "chrome.exe")


def test_signature_check_quotes_path_and_accepts_valid_chrome(desktop, monkeypatch, tmp_path):
    target = tmp_path / "O'Brien" / "chrome.exe"
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "powershell.exe")

    def run(command, **kwargs):
        script = base64.b64decode(command[-1]).decode("utf-16-le")
        assert "O''Brien" in script
        assert "Get-AuthenticodeSignature -LiteralPath" in script
        assert "$env:PSModulePath = Join-Path $PSHOME 'Modules'" in script
        payload = dict(status="Valid", publisher="Google LLC", product="Google Chrome", version="154.0.0.1", original="chrome.exe")
        return subprocess.CompletedProcess(command, 0, "\ufeff" + json.dumps(payload), "")

    monkeypatch.setattr(desktop, "_run", run)
    assert desktop._google_signed_file(target)["version"] == "154.0.0.1"


@pytest.mark.parametrize("variable", ["LOCALAPPDATA", "PROGRAMW6432", "PROGRAMFILES", "PROGRAMFILES(X86)"])
def test_existing_chrome_is_verified_without_winget(desktop, monkeypatch, tmp_path, variable):
    target = tmp_path / variable / "Google/Chrome/Application/chrome.exe"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"fixture")
    checked = []

    def verify(path):
        checked.append(path)
        return {"binary": str(path), "version": "154.0.0.1"}

    monkeypatch.setattr(desktop, "_google_signed_file", verify)
    monkeypatch.setattr(desktop.shutil, "which", lambda _: pytest.fail("must not require winget"))
    result = desktop.setup_desktop_app("chrome")
    assert result["status"] == "already_installed" and result["verified"]
    assert checked == [target]


def test_invalid_existing_chrome_is_not_overwritten(desktop, monkeypatch, tmp_path):
    target = tmp_path / "LOCALAPPDATA/Google/Chrome/Application/chrome.exe"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"invalid fixture")

    def reject(path):
        raise RuntimeError("signature invalid")

    monkeypatch.setattr(desktop, "_google_signed_file", reject)
    monkeypatch.setattr(desktop, "_run", lambda *a, **k: pytest.fail("must not install"))
    with pytest.raises(RuntimeError, match="signature invalid"):
        desktop.setup_desktop_app("chrome", yes=True)
    assert target.read_bytes() == b"invalid fixture"


@pytest.mark.parametrize("record_before", [False, True])
def test_chrome_record_without_binary_is_failure(desktop, monkeypatch, record_before):
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "winget.exe")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        present = record_before or len(calls) > 1
        return subprocess.CompletedProcess(command, 0, "Google.Chrome.EXE 154" if present else "", "")

    monkeypatch.setattr(desktop, "_run", run)
    with pytest.raises(RuntimeError, match="signed chrome.exe"):
        desktop.setup_desktop_app("chrome", yes=True)
    assert len(calls) == (1 if record_before else 3)


@pytest.mark.parametrize("suffix", [".Beta", "-Preview", "Extra"])
def test_package_verification_rejects_partial_id(desktop, monkeypatch, suffix):
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "winget.exe")
    monkeypatch.setattr(desktop, "_run", lambda command, **k: subprocess.CompletedProcess(
        command, 0, "liule.Snipaste" + suffix, "",
    ))
    with pytest.raises(RuntimeError, match="no matching WinGet package"):
        desktop.setup_desktop_app("snipaste", yes=True)


def test_installer_failure_never_claims_success(desktop, monkeypatch):
    monkeypatch.setattr(desktop.shutil, "which", lambda _: "winget.exe")

    def run(command, **kwargs):
        if command[1] == "install":
            raise RuntimeError("installer hash mismatch")
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(desktop, "_run", run)
    result = CliRunner().invoke(main, ["chrome", "--yes"])
    assert result.exit_code != 0
    assert "installer hash mismatch" in result.output
    assert "Installation verified" not in result.output
