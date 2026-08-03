from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

import chatup.chromedriver as public_api
from chatup.cli import main
from chatup.runtime.chromedriver import (
    ChromeDriverError,
    ChromeDriverInstallation,
    doctor_chromedriver,
    garbage_collect_chromedriver,
    install_chromedriver,
    list_chromedrivers,
    normalize_chromedriver_platform,
    read_browser_version,
    remove_chromedriver,
    resolve_chromedriver,
    resolve_chromedriver_download,
    resolve_chromedriver_for_browser_version,
    safe_extract_chromedriver_zip,
)


def _archive(
    path: Path,
    *,
    platform: str = "mac-arm64",
    payload: bytes = b"chromedriver",
) -> Path:
    binaries = {
        "mac-arm64": "chromedriver-mac-arm64/chromedriver",
        "mac-x64": "chromedriver-mac-x64/chromedriver",
        "linux64": "chromedriver-linux64/chromedriver",
        "win64": "chromedriver-win64/chromedriver.exe",
    }
    with zipfile.ZipFile(path, "w") as bundle:
        info = zipfile.ZipInfo(binaries[platform])
        info.external_attr = 0o755 << 16
        bundle.writestr(info, payload)
    return path


def _resolver(version: str, *, driver_platform: str | None = None):
    assert version in {"stable", "145.0.1.2"}
    return (
        "145.0.1.2",
        driver_platform or "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/chromedriver.zip",
    )


def _install(tmp_path: Path) -> ChromeDriverInstallation:
    archive = _archive(tmp_path / "driver.zip")

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    return install_chromedriver(
        "stable",
        home=tmp_path / "chromedriver",
        driver_platform="mac-arm64",
        resolver=_resolver,
        downloader=downloader,
    )


def test_normalize_chromedriver_platform_maps_supported_hosts():
    assert (
        normalize_chromedriver_platform(system="Darwin", machine="arm64")
        == "mac-arm64"
    )
    assert (
        normalize_chromedriver_platform(system="Darwin", machine="x86_64")
        == "mac-x64"
    )
    assert (
        normalize_chromedriver_platform(system="Linux", machine="amd64")
        == "linux64"
    )
    assert (
        normalize_chromedriver_platform(system="Windows", machine="AMD64")
        == "win64"
    )

    with pytest.raises(ChromeDriverError, match="does not provide"):
        normalize_chromedriver_platform(system="Linux", machine="aarch64")


def test_public_chromedriver_api_is_backend_specific():
    assert public_api.DEFAULT_HOME.name == "chromedriver"
    assert callable(public_api.install)
    assert callable(public_api.ensure)
    assert callable(public_api.resolve)
    assert callable(public_api.list_installations)
    assert callable(public_api.doctor)
    assert callable(public_api.remove)
    assert callable(public_api.gc)
    assert callable(public_api.read_browser_version)
    assert callable(public_api.resolve_for_browser_version)


def test_resolve_chromedriver_download_uses_driver_artifact():
    channel_payload = {
        "channels": {
            "Stable": {
                "version": "145.0.1.2",
                "downloads": {
                    "chrome": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
                        }
                    ],
                    "chromedriver": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/driver-stable.zip",
                        }
                    ],
                },
            }
        }
    }
    exact_payload = {
        "versions": [
            {
                "version": "145.0.1.2",
                "downloads": {
                    "chromedriver": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/driver-exact.zip",
                        }
                    ]
                },
            }
        ]
    }

    def fetcher(url: str):
        return channel_payload if "last-known-good" in url else exact_payload

    assert resolve_chromedriver_download(
        "stable", driver_platform="mac-arm64", fetcher=fetcher
    ) == (
        "145.0.1.2",
        "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/driver-stable.zip",
    )
    assert resolve_chromedriver_download(
        "145.0.1.2", driver_platform="mac-arm64", fetcher=fetcher
    ) == (
        "145.0.1.2",
        "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/driver-exact.zip",
    )


@pytest.mark.parametrize(
    ("version", "payload"),
    [("stable", {"channels": []}), ("145.0.1.2", {"versions": {}})],
)
def test_resolve_chromedriver_download_rejects_malformed_manifest(
    version,
    payload,
):
    with pytest.raises(ChromeDriverError, match="version not found"):
        resolve_chromedriver_download(
            version,
            driver_platform="mac-arm64",
            fetcher=lambda _url: payload,
        )


def test_resolve_chromedriver_for_browser_version_prefers_build_match():
    payload = {
        "builds": {
            "145.0.7632": {
                "version": "145.0.7632.10",
                "downloads": {
                    "chromedriver": [
                        {
                            "platform": "mac-arm64",
                            "url": "https://storage.googleapis.com/chrome-for-testing-public/build-driver.zip",
                        }
                    ]
                },
            }
        }
    }
    seen: list[str] = []

    def fetcher(url: str):
        seen.append(url)
        return payload

    assert resolve_chromedriver_for_browser_version(
        "145.0.7632.77",
        driver_platform="mac-arm64",
        fetcher=fetcher,
    ) == (
        "145.0.7632.10",
        "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/build-driver.zip",
    )
    assert len(seen) == 1


def test_resolve_chromedriver_for_browser_version_falls_back_to_milestone():
    milestone_entry = {
        "milestone": "145",
        "version": "145.0.7632.20",
        "downloads": {
            "chromedriver": [
                {
                    "platform": "mac-arm64",
                    "url": "https://storage.googleapis.com/chrome-for-testing-public/milestone-driver.zip",
                }
            ]
        },
    }

    def fetcher(url: str):
        if "latest-patch" in url:
            return {"builds": {}}
        return {"milestones": {"145": milestone_entry}}

    resolved = resolve_chromedriver_for_browser_version(
        "145.0.7632.77",
        driver_platform="mac-arm64",
        fetcher=fetcher,
    )
    assert resolved[0] == "145.0.7632.20"


def test_read_browser_version_parses_real_product_shapes(tmp_path):
    browser = tmp_path / "browser"
    browser.write_text("binary")

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[str(browser), "--version"],
            returncode=0,
            stdout="Google Chrome for Testing 145.0.1.2\n",
            stderr="",
        )

    assert read_browser_version(browser, runner=runner) == "145.0.1.2"


def test_install_can_match_browser_or_cft_version(tmp_path):
    archive = _archive(tmp_path / "driver.zip")
    requested: list[str] = []
    matched: list[str] = []

    def resolver(version: str, *, driver_platform: str | None = None):
        requested.append(version)
        return _resolver(version, driver_platform=driver_platform)

    def browser_match_resolver(
        version: str,
        *,
        driver_platform: str | None = None,
    ):
        matched.append(version)
        return _resolver("145.0.1.2", driver_platform=driver_platform)

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    installation = install_chromedriver(
        match_browser=tmp_path / "browser",
        home=tmp_path / "from-browser",
        driver_platform="mac-arm64",
        resolver=resolver,
        browser_match_resolver=browser_match_resolver,
        downloader=downloader,
        browser_version_reader=lambda _path: "145.0.1.2",
    )
    assert installation.matched_browser_version == "145.0.1.2"

    cft_installation = install_chromedriver(
        match_cft_version="145.0.1.2",
        home=tmp_path / "from-cft",
        driver_platform="mac-arm64",
        resolver=resolver,
        downloader=downloader,
    )
    assert cft_installation.matched_browser_version == "145.0.1.2"
    assert matched == ["145.0.1.2"]
    assert requested == ["145.0.1.2"]

    with pytest.raises(ChromeDriverError, match="Choose only one"):
        install_chromedriver(
            "stable",
            match_cft_version="145.0.1.2",
            home=tmp_path,
        )


def test_install_resolve_list_and_doctor_without_execution(tmp_path):
    archive = _archive(tmp_path / "driver.zip")
    expected_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    home = tmp_path / "chromedriver"
    installation = install_chromedriver(
        "stable",
        home=home,
        driver_platform="mac-arm64",
        expected_sha256=expected_sha256,
        resolver=_resolver,
        downloader=downloader,
    )

    assert installation.ref == "chromedriver@145.0.1.2"
    assert installation.root_dir == home / "145.0.1.2" / "mac-arm64"
    assert installation.binary_path.is_file()
    assert (installation.root_dir / "installation.json").is_file()
    assert resolve_chromedriver(
        "145.0.1.2", home=home, driver_platform="mac-arm64"
    ) == installation
    assert list_chromedrivers(home=home) == [installation]
    assert doctor_chromedriver(installation, execute=False)["status"] == "ready"


@pytest.mark.parametrize(
    "platform_name",
    ["mac-arm64", "mac-x64", "linux64", "win64"],
)
def test_install_supports_each_chromedriver_archive_layout(tmp_path, platform_name):
    archive = _archive(tmp_path / f"{platform_name}.zip", platform=platform_name)

    def resolver(_version: str, *, driver_platform: str | None = None):
        assert driver_platform == platform_name
        return (
            "145.0.1.2",
            platform_name,
            f"https://storage.googleapis.com/chrome-for-testing-public/{platform_name}.zip",
        )

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    installation = install_chromedriver(
        "145.0.1.2",
        home=tmp_path / "chromedriver",
        driver_platform=platform_name,
        resolver=resolver,
        downloader=downloader,
    )

    assert installation.platform == platform_name
    assert installation.binary_path.is_file()


def test_chromedriver_rejects_tampered_metadata_and_old_ref_shape(tmp_path):
    with pytest.raises(ChromeDriverError, match="requires an exact version"):
        resolve_chromedriver(
            "chromedriver@145.0.1.2",
            home=tmp_path,
            driver_platform="mac-arm64",
        )

    installation = _install(tmp_path)
    metadata_path = installation.root_dir / "installation.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["kind"] = "chrome-for-testing"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ChromeDriverError, match="Unexpected kind"):
        resolve_chromedriver(
            "145.0.1.2",
            home=tmp_path / "chromedriver",
            driver_platform="mac-arm64",
        )


def test_chromedriver_rejects_non_object_metadata(tmp_path):
    installation = _install(tmp_path)
    metadata_path = installation.root_dir / "installation.json"
    metadata_path.write_text("[]")

    with pytest.raises(ChromeDriverError, match="must be a JSON object"):
        resolve_chromedriver(
            "145.0.1.2",
            home=tmp_path / "chromedriver",
            driver_platform="mac-arm64",
        )


def test_chromedriver_force_install_rejects_symlink_root(tmp_path):
    home = tmp_path / "chromedriver"
    outside = tmp_path / "outside"
    outside.mkdir()
    install_dir = home / "145.0.1.2" / "mac-arm64"
    install_dir.parent.mkdir(parents=True)
    install_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ChromeDriverError, match="symlink"):
        install_chromedriver(
            "stable",
            home=home,
            driver_platform="mac-arm64",
            force=True,
            resolver=_resolver,
        )


def test_install_rejects_non_official_url_before_download(tmp_path):
    called = False

    def resolver(_version: str, *, driver_platform: str | None = None):
        return (
            "145.0.1.2",
            driver_platform or "mac-arm64",
            "https://example.invalid/chromedriver.zip",
        )

    def downloader(_url: str, _destination: Path):
        nonlocal called
        called = True

    with pytest.raises(ChromeDriverError, match="official Google storage"):
        install_chromedriver(
            "stable",
            home=tmp_path,
            driver_platform="mac-arm64",
            resolver=resolver,
            downloader=downloader,
        )
    assert not called


def test_driver_extract_wrapper_preserves_backend_error(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape", "bad")

    with pytest.raises(ChromeDriverError, match="Unsafe path in ChromeDriver"):
        safe_extract_chromedriver_zip(archive, tmp_path / "output")


def test_remove_and_gc_are_scoped_to_chromedriver_home(tmp_path):
    installation = _install(tmp_path)
    home = tmp_path / "chromedriver"
    removed = remove_chromedriver(
        installation.version,
        home=home,
        driver_platform=installation.platform,
    )
    assert removed == installation
    assert not installation.root_dir.exists()

    stale = home / "145.0.1.3" / ".mac-arm64-install-stale"
    stale.mkdir(parents=True)
    old = time.time() - 48 * 60 * 60
    stale.touch()
    os.utime(stale, (old, old))
    preview = garbage_collect_chromedriver(
        home=home,
        dry_run=True,
        minimum_age_seconds=24 * 60 * 60,
    )
    assert preview["candidates"] == [str(stale)]

    result = garbage_collect_chromedriver(
        home=home,
        dry_run=False,
        yes=True,
        minimum_age_seconds=24 * 60 * 60,
    )
    assert result["removed"] == [str(stale)]
    assert not stale.exists()


def test_chromedriver_install_json_output_is_machine_readable(monkeypatch, tmp_path):
    installation = ChromeDriverInstallation(
        kind="chromedriver",
        version="145.0.1.2",
        platform="mac-arm64",
        root_dir=tmp_path / "installation",
        binary_path=tmp_path / "installation" / "chromedriver",
        source_url="https://storage.googleapis.com/chrome-for-testing-public/chromedriver.zip",
        archive_sha256="b" * 64,
        installed_at="2026-08-04T00:00:00+00:00",
        matched_browser_version="145.0.1.2",
    )
    installation.binary_path.parent.mkdir(parents=True)
    installation.binary_path.write_text("chromedriver")
    monkeypatch.setattr(public_api, "install", lambda *args, **kwargs: installation)
    monkeypatch.setattr(
        public_api,
        "doctor",
        lambda *_args, **_kwargs: {
            **installation.to_dict(),
            "status": "ready",
            "reported_version": "ChromeDriver 145.0.1.2",
            "errors": [],
        },
    )

    result = CliRunner().invoke(
        main,
        [
            "chromedriver",
            "install",
            "--match-cft-version",
            "145.0.1.2",
            "--output",
            "json",
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["kind"] == "chromedriver"
    assert payload["matched_browser_version"] == "145.0.1.2"


def test_chromedriver_cli_rejects_conflicting_install_selectors(tmp_path):
    browser = tmp_path / "browser"
    browser.write_text("browser")
    result = CliRunner().invoke(
        main,
        [
            "chromedriver",
            "install",
            "--version",
            "145.0.1.2",
            "--match-browser",
            str(browser),
            "-I",
        ],
    )

    assert result.exit_code != 0
    assert "Use only one" in result.output


def test_chromedriver_remove_requires_yes():
    result = CliRunner().invoke(
        main,
        ["chromedriver", "remove", "145.0.1.2", "-I"],
    )

    assert result.exit_code != 0
    assert "Refusing to remove without --yes" in result.output
