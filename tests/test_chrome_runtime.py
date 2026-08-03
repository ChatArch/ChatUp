from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from chatup.cli import main
from chatup.chrome import ensure_chrome, install_chrome, resolve_chrome
from chatup.runtime.browser import (
    BrowserRuntime,
    BrowserRuntimeError,
    doctor_browser_runtime,
    install_chrome_for_testing,
    list_browser_runtimes,
    normalize_cft_platform,
    resolve_browser_runtime,
    resolve_chrome_for_testing_download,
    safe_extract_zip,
)


def _archive(path: Path, *, platform: str = "mac-arm64", payload: bytes = b"chrome") -> Path:
    binaries = {
        "mac-arm64": "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "mac-x64": "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "linux64": "chrome-linux64/chrome",
        "win64": "chrome-win64/chrome.exe",
    }
    with zipfile.ZipFile(path, "w") as bundle:
        info = zipfile.ZipInfo(binaries[platform])
        info.external_attr = 0o755 << 16
        bundle.writestr(info, payload)
    return path


def _resolver(version: str, *, cft_platform: str | None = None):
    assert version in {"stable", "145.0.1.2"}
    return "145.0.1.2", cft_platform or "mac-arm64", "https://storage.googleapis.com/chrome-for-testing-public/chrome.zip"


def test_normalize_cft_platform_maps_supported_hosts():
    assert normalize_cft_platform(system="Darwin", machine="arm64") == "mac-arm64"
    assert normalize_cft_platform(system="Darwin", machine="x86_64") == "mac-x64"
    assert normalize_cft_platform(system="Linux", machine="amd64") == "linux64"
    assert normalize_cft_platform(system="Windows", machine="AMD64") == "win64"

    with pytest.raises(BrowserRuntimeError, match="does not provide"):
        normalize_cft_platform(system="Linux", machine="aarch64")


def test_public_chrome_facade_exports_consumer_contract():
    assert callable(install_chrome)
    assert callable(ensure_chrome)
    assert callable(resolve_chrome)


def test_resolve_chrome_download_supports_channel_and_exact_version():
    channel_payload = {
        "channels": {
            "Stable": {
                "version": "145.0.1.2",
                "downloads": {
                    "chrome": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/stable.zip",
                        }
                    ]
                },
            }
        }
    }
    exact_payload = {
        "versions": [
            {
                "version": "145.0.1.2",
                "downloads": {
                    "chrome": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/exact.zip",
                        }
                    ]
                },
            }
        ]
    }

    def fetcher(url: str):
        return channel_payload if "last-known-good" in url else exact_payload

    assert resolve_chrome_for_testing_download(
        "stable", cft_platform="mac-arm64", fetcher=fetcher
    ) == ("145.0.1.2", "mac-arm64", "https://storage.googleapis.com/chrome-for-testing-public/stable.zip")
    assert resolve_chrome_for_testing_download(
        "145.0.1.2", cft_platform="mac-arm64", fetcher=fetcher
    ) == ("145.0.1.2", "mac-arm64", "https://storage.googleapis.com/chrome-for-testing-public/exact.zip")


def test_install_resolve_list_and_doctor_without_execution(tmp_path):
    archive = _archive(tmp_path / "source.zip")
    expected_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    home = tmp_path / "chatarch" / "chrome"
    runtime = install_chrome_for_testing(
        "stable",
        home=home,
        cft_platform="mac-arm64",
        expected_sha256=expected_sha256,
        resolver=_resolver,
        downloader=downloader,
    )

    assert runtime.ref == "chrome-for-testing@145.0.1.2"
    assert runtime.binary_path.is_file()
    assert runtime.root_dir == home / "chrome-for-testing" / "145.0.1.2" / "mac-arm64"
    assert json.loads((runtime.root_dir / "runtime.json").read_text())["archive_sha256"] == expected_sha256
    assert resolve_browser_runtime(
        runtime.ref, home=home, cft_platform="mac-arm64"
    ) == runtime
    assert list_browser_runtimes(home=home) == [runtime]
    assert doctor_browser_runtime(runtime, execute=False)["status"] == "ready"

    with pytest.raises(BrowserRuntimeError, match="Installed browser SHA-256"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            expected_sha256="0" * 64,
            resolver=_resolver,
            downloader=downloader,
        )


@pytest.mark.parametrize("platform_name", ["mac-arm64", "mac-x64", "linux64", "win64"])
def test_install_supports_each_cft_archive_layout(tmp_path, platform_name):
    archive = _archive(tmp_path / f"{platform_name}.zip", platform=platform_name)

    def resolver(_version: str, *, cft_platform: str | None = None):
        assert cft_platform == platform_name
        return (
            "145.0.1.2",
            platform_name,
            f"https://storage.googleapis.com/chrome-for-testing-public/{platform_name}.zip",
        )

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    runtime = install_chrome_for_testing(
        "145.0.1.2",
        home=tmp_path / "chrome",
        cft_platform=platform_name,
        resolver=resolver,
        downloader=downloader,
    )

    assert runtime.platform == platform_name
    assert runtime.binary_path.is_file()


def test_resolve_rejects_tampered_runtime_metadata(tmp_path):
    archive = _archive(tmp_path / "source.zip")

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    runtime = install_chrome_for_testing(
        "stable",
        home=tmp_path / "chrome",
        cft_platform="mac-arm64",
        resolver=_resolver,
        downloader=downloader,
    )
    metadata_path = runtime.root_dir / "runtime.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["binary_path"] = "other/chrome"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(BrowserRuntimeError, match="Unexpected browser executable path"):
        resolve_browser_runtime(
            runtime.ref,
            home=tmp_path / "chrome",
            cft_platform="mac-arm64",
        )


def test_force_failure_preserves_existing_runtime(tmp_path):
    first_archive = _archive(tmp_path / "first.zip", payload=b"first")
    bad_archive = _archive(tmp_path / "bad.zip", payload=b"bad")
    home = tmp_path / "chrome"

    def first_download(_url: str, destination: Path):
        destination.write_bytes(first_archive.read_bytes())

    original = install_chrome_for_testing(
        "stable",
        home=home,
        cft_platform="mac-arm64",
        resolver=_resolver,
        downloader=first_download,
    )
    original_bytes = original.binary_path.read_bytes()

    def bad_download(_url: str, destination: Path):
        destination.write_bytes(bad_archive.read_bytes())

    with pytest.raises(BrowserRuntimeError, match="SHA-256 mismatch"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            expected_sha256="0" * 64,
            force=True,
            resolver=_resolver,
            downloader=bad_download,
        )

    assert original.binary_path.read_bytes() == original_bytes
    assert resolve_browser_runtime(
        original.ref, home=home, cft_platform="mac-arm64"
    ).archive_sha256 == original.archive_sha256


def test_install_rejects_non_official_archive_url_before_download(tmp_path):
    called = False

    def resolver(_version: str, *, cft_platform: str | None = None):
        return "145.0.1.2", cft_platform or "mac-arm64", "https://example.invalid/chrome.zip"

    def downloader(_url: str, _destination: Path):
        nonlocal called
        called = True

    with pytest.raises(BrowserRuntimeError, match="official Google storage"):
        install_chrome_for_testing(
            "stable",
            home=tmp_path,
            cft_platform="mac-arm64",
            resolver=resolver,
            downloader=downloader,
        )
    assert not called


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape", "bad")

    with pytest.raises(BrowserRuntimeError, match="Unsafe path"):
        safe_extract_zip(archive, tmp_path / "output")
    assert not (tmp_path / "escape").exists()


def test_safe_extract_allows_internal_symlink_and_rejects_escape(tmp_path):
    internal = tmp_path / "internal.zip"
    with zipfile.ZipFile(internal, "w") as bundle:
        bundle.writestr("app/Versions/1/chrome", "binary")
        link = zipfile.ZipInfo("app/Versions/Current")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "1")

    destination = tmp_path / "internal-output"
    safe_extract_zip(internal, destination)
    assert (destination / "app/Versions/Current").is_symlink()
    assert (destination / "app/Versions/Current/chrome").read_text() == "binary"

    escaping = tmp_path / "escaping.zip"
    with zipfile.ZipFile(escaping, "w") as bundle:
        link = zipfile.ZipInfo("app/escape")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "../../outside")

    with pytest.raises(BrowserRuntimeError, match="Symlink escapes"):
        safe_extract_zip(escaping, tmp_path / "escaping-output")


def test_chrome_help_matches_flat_cli_contract():
    root = CliRunner().invoke(main, ["--help"])
    chrome = CliRunner().invoke(main, ["chrome", "--help"])

    assert root.exit_code == 0
    assert "chrome" in root.output
    assert "browser" not in root.output
    assert chrome.exit_code == 0
    for option in (
        "--version",
        "--home",
        "--platform",
        "--sha256",
        "--force",
        "--doctor / --no-doctor",
        "--output",
        "--interactive",
    ):
        assert option in chrome.output
    assert "Chromedriver" not in chrome.output


def test_setup_chrome_json_output_is_machine_readable(monkeypatch, tmp_path):
    import chatup.setup.chrome as chrome_module

    runtime = BrowserRuntime(
        kind="chrome-for-testing",
        version="145.0.1.2",
        platform="mac-arm64",
        root_dir=tmp_path / "runtime",
        binary_path=tmp_path / "runtime" / "chrome",
        source_url="https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
        archive_sha256="a" * 64,
        installed_at="2026-08-03T00:00:00+00:00",
    )
    runtime.binary_path.parent.mkdir(parents=True)
    runtime.binary_path.write_text("chrome")

    monkeypatch.setattr(chrome_module, "install_chrome", lambda *args, **kwargs: runtime)
    monkeypatch.setattr(
        chrome_module,
        "doctor_browser_runtime",
        lambda *_args, **_kwargs: {
            **runtime.to_dict(),
            "status": "ready",
            "reported_version": "Google Chrome for Testing 145.0.1.2",
            "errors": [],
        },
    )

    result = CliRunner().invoke(
        main,
        ["chrome", "--version", "145.0.1.2", "--output", "json", "-I"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["binary_path"] == str(runtime.binary_path)
    assert payload["status"] == "ready"
