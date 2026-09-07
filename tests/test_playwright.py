import json
import subprocess

import pytest

from chatup.runtime.playwright import (
    PlaywrightError,
    _InstalledPayload,
    doctor_playwright_browser,
    install_playwright_browser,
    resolve_playwright_browser,
)

RUNTIME = {
    "node_bin": "/managed/node",
    "npm_bin": "/managed/npm",
    "node_version": "v22.1.0",
    "npm_version": "10.8.0",
    "node_major": 22,
    "source": "test",
}


def _installer(version, browser, staging_dir, *, runtime):
    assert version == "1.61.1"
    assert browser == "chromium"
    assert runtime == RUNTIME
    (staging_dir / "package").mkdir()
    binary = staging_dir / "browsers" / "chromium-1228" / "chrome"
    binary.parent.mkdir(parents=True)
    binary.write_text("browser", encoding="utf-8")
    binary.chmod(0o755)
    return _InstalledPayload(
        browser_revision="1228",
        browser_version="149.0.7827.55",
        binary_path=binary,
        node_version="v22.1.0",
    )


def test_install_resolve_and_static_doctor(tmp_path):
    home = tmp_path / "playwright"
    installation = install_playwright_browser(
        "1.61.1",
        home=home,
        runtime_resolver=lambda: RUNTIME,
        installer=_installer,
    )

    assert installation.ref == "playwright@1.61.1/chromium"
    assert installation.browser_revision == "1228"
    assert installation.browser_version == "149.0.7827.55"
    assert installation.binary_path.is_file()
    assert installation.package_dir.is_dir()
    assert installation.browsers_dir.is_dir()
    assert resolve_playwright_browser("1.61.1", home=home) == installation
    assert doctor_playwright_browser(installation, execute=False)["status"] == "ready"


def test_install_reuses_valid_metadata_without_node(tmp_path):
    home = tmp_path / "playwright"
    first = install_playwright_browser(
        "1.61.1",
        home=home,
        runtime_resolver=lambda: RUNTIME,
        installer=_installer,
    )

    second = install_playwright_browser(
        "1.61.1",
        home=home,
        runtime_resolver=lambda: (_ for _ in ()).throw(AssertionError("not called")),
        installer=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("not called")),
    )
    assert second == first


def test_install_requires_exact_version_supported_browser_and_node(tmp_path):
    with pytest.raises(PlaywrightError, match="three-component"):
        install_playwright_browser("latest", home=tmp_path)
    with pytest.raises(PlaywrightError, match="Unsupported"):
        install_playwright_browser("1.61.1", browser="firefox", home=tmp_path)
    with pytest.raises(PlaywrightError, match="chatup nodejs"):
        install_playwright_browser(
            "1.61.1",
            home=tmp_path,
            runtime_resolver=dict,
        )


def test_install_rejects_parent_symlink_escape(tmp_path):
    home = tmp_path / "playwright"
    outside = tmp_path / "outside"
    outside.mkdir()
    home.mkdir()
    (home / "1.61.1").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PlaywrightError, match="escapes its managed home"):
        install_playwright_browser(
            "1.61.1",
            home=home,
            runtime_resolver=lambda: RUNTIME,
            installer=_installer,
        )


def test_failed_force_install_preserves_existing_installation(tmp_path):
    home = tmp_path / "playwright"
    original = install_playwright_browser(
        "1.61.1",
        home=home,
        runtime_resolver=lambda: RUNTIME,
        installer=_installer,
    )

    def fail(*_args, **_kwargs):
        raise PlaywrightError("install failed")

    with pytest.raises(PlaywrightError, match="install failed"):
        install_playwright_browser(
            "1.61.1",
            home=home,
            force=True,
            runtime_resolver=lambda: RUNTIME,
            installer=fail,
        )
    assert resolve_playwright_browser("1.61.1", home=home) == original


def test_doctor_reports_executable_version(tmp_path):
    installation = install_playwright_browser(
        "1.61.1",
        home=tmp_path / "playwright",
        runtime_resolver=lambda: RUNTIME,
        installer=_installer,
    )

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, "Google Chrome for Testing 149.0.7827.55\n", "")

    health = doctor_playwright_browser(installation, runner=runner)
    assert health["status"] == "ready"
    assert health["observed_version"] == "Google Chrome for Testing 149.0.7827.55"


def test_metadata_path_tampering_is_rejected(tmp_path):
    home = tmp_path / "playwright"
    installation = install_playwright_browser(
        "1.61.1",
        home=home,
        runtime_resolver=lambda: RUNTIME,
        installer=_installer,
    )
    metadata = installation.root_dir / "installation.json"
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    payload["binary_path"] = str(tmp_path / "outside-browser")
    metadata.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PlaywrightError, match="escapes"):
        resolve_playwright_browser("1.61.1", home=home)
