from __future__ import annotations

import hashlib
import json
import os
import stat
import time
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

import chatup.chrome_for_testing as public_api
from chatup.cli import main
from chatup.runtime.chrome_for_testing import (
    ChromeForTestingError,
    ChromeForTestingInstallation,
    doctor_chrome_for_testing,
    garbage_collect_chrome_for_testing,
    install_chrome_for_testing,
    list_chrome_for_testing,
    normalize_cft_platform,
    remove_chrome_for_testing,
    resolve_chrome_for_testing,
    resolve_chrome_for_testing_download,
    safe_extract_chrome_for_testing_zip,
)


def _archive(
    path: Path,
    *,
    platform: str = "mac-arm64",
    payload: bytes = b"chrome",
) -> Path:
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
    return (
        "145.0.1.2",
        cft_platform or "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
    )


def _install(tmp_path: Path) -> ChromeForTestingInstallation:
    archive = _archive(tmp_path / "source.zip")

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    return install_chrome_for_testing(
        "stable",
        home=tmp_path / "chrome-for-testing",
        cft_platform="mac-arm64",
        resolver=_resolver,
        downloader=downloader,
    )


def test_normalize_cft_platform_maps_supported_hosts():
    assert normalize_cft_platform(system="Darwin", machine="arm64") == "mac-arm64"
    assert normalize_cft_platform(system="Darwin", machine="x86_64") == "mac-x64"
    assert normalize_cft_platform(system="Linux", machine="amd64") == "linux64"
    assert normalize_cft_platform(system="Windows", machine="AMD64") == "win64"

    with pytest.raises(ChromeForTestingError, match="does not provide"):
        normalize_cft_platform(system="Linux", machine="aarch64")


def test_public_cft_api_is_backend_specific():
    assert public_api.DEFAULT_HOME.name == "chrome-for-testing"
    assert callable(public_api.install)
    assert callable(public_api.ensure)
    assert callable(public_api.resolve)
    assert callable(public_api.list_installations)
    assert callable(public_api.doctor)
    assert callable(public_api.remove)
    assert callable(public_api.gc)


def test_resolve_cft_download_supports_channel_and_exact_version():
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
    ) == (
        "145.0.1.2",
        "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/stable.zip",
    )
    assert resolve_chrome_for_testing_download(
        "145.0.1.2", cft_platform="mac-arm64", fetcher=fetcher
    ) == (
        "145.0.1.2",
        "mac-arm64",
        "https://storage.googleapis.com/chrome-for-testing-public/exact.zip",
    )


@pytest.mark.parametrize(
    ("version", "payload"),
    [("stable", {"channels": []}), ("145.0.1.2", {"versions": {}})],
)
def test_resolve_cft_download_rejects_malformed_manifest(version, payload):
    with pytest.raises(ChromeForTestingError, match="version not found"):
        resolve_chrome_for_testing_download(
            version,
            cft_platform="mac-arm64",
            fetcher=lambda _url: payload,
        )


def test_install_resolve_list_and_doctor_without_execution(tmp_path):
    archive = _archive(tmp_path / "source.zip")
    expected_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    def downloader(_url: str, destination: Path):
        destination.write_bytes(archive.read_bytes())

    home = tmp_path / "chrome-for-testing"
    installation = install_chrome_for_testing(
        "stable",
        home=home,
        cft_platform="mac-arm64",
        expected_sha256=expected_sha256,
        resolver=_resolver,
        downloader=downloader,
    )

    assert installation.ref == "chrome-for-testing@145.0.1.2"
    assert installation.binary_path.is_file()
    assert installation.root_dir == home / "145.0.1.2" / "mac-arm64"
    metadata_path = installation.root_dir / "installation.json"
    assert json.loads(metadata_path.read_text())["archive_sha256"] == expected_sha256
    assert resolve_chrome_for_testing(
        "145.0.1.2", home=home, cft_platform="mac-arm64"
    ) == installation
    assert list_chrome_for_testing(home=home) == [installation]
    assert doctor_chrome_for_testing(installation, execute=False)["status"] == "ready"

    with pytest.raises(ChromeForTestingError, match="Installed Chrome for Testing"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            expected_sha256="0" * 64,
            resolver=_resolver,
            downloader=downloader,
        )


@pytest.mark.parametrize(
    "platform_name",
    ["mac-arm64", "mac-x64", "linux64", "win64"],
)
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

    installation = install_chrome_for_testing(
        "145.0.1.2",
        home=tmp_path / "chrome-for-testing",
        cft_platform=platform_name,
        resolver=resolver,
        downloader=downloader,
    )

    assert installation.platform == platform_name
    assert installation.binary_path.is_file()


def test_resolution_requires_exact_version_and_rejects_old_aliases(tmp_path):
    for value in ("stable", "chrome@145.0.1.2", "cft@145.0.1.2"):
        with pytest.raises(ChromeForTestingError, match="requires an exact version"):
            resolve_chrome_for_testing(
                value,
                home=tmp_path,
                cft_platform="mac-arm64",
            )


def test_resolve_rejects_tampered_metadata(tmp_path):
    installation = _install(tmp_path)
    metadata_path = installation.root_dir / "installation.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["binary_path"] = "other/chrome"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ChromeForTestingError, match="Unexpected browser executable"):
        resolve_chrome_for_testing(
            "145.0.1.2",
            home=tmp_path / "chrome-for-testing",
            cft_platform="mac-arm64",
        )


def test_resolve_rejects_non_object_metadata(tmp_path):
    installation = _install(tmp_path)
    metadata_path = installation.root_dir / "installation.json"
    metadata_path.write_text("[]")

    with pytest.raises(ChromeForTestingError, match="must be a JSON object"):
        resolve_chrome_for_testing(
            "145.0.1.2",
            home=tmp_path / "chrome-for-testing",
            cft_platform="mac-arm64",
        )


def test_force_install_rejects_symlink_root(tmp_path):
    home = tmp_path / "chrome-for-testing"
    outside = tmp_path / "outside"
    outside.mkdir()
    install_dir = home / "145.0.1.2" / "mac-arm64"
    install_dir.parent.mkdir(parents=True)
    install_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ChromeForTestingError, match="symlink"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            force=True,
            resolver=_resolver,
        )


def test_install_rejects_untrusted_resolver_identity_and_parent_symlink(tmp_path):
    home = tmp_path / "chrome-for-testing"
    downloaded = False

    def downloader(_url: str, _destination: Path):
        nonlocal downloaded
        downloaded = True

    def invalid_resolver(_version: str, *, cft_platform: str | None = None):
        return (
            "../../escape",
            cft_platform or "mac-arm64",
            "https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
        )

    with pytest.raises(ChromeForTestingError, match="invalid version"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            resolver=invalid_resolver,
            downloader=downloader,
        )
    assert not downloaded

    outside = tmp_path / "outside"
    outside.mkdir()
    home.mkdir()
    (home / "145.0.1.2").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ChromeForTestingError, match="escapes its managed home"):
        install_chrome_for_testing(
            "stable",
            home=home,
            cft_platform="mac-arm64",
            resolver=_resolver,
            downloader=downloader,
        )
    assert not downloaded


def test_force_failure_preserves_existing_installation(tmp_path):
    first_archive = _archive(tmp_path / "first.zip", payload=b"first")
    bad_archive = _archive(tmp_path / "bad.zip", payload=b"bad")
    home = tmp_path / "chrome-for-testing"

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

    with pytest.raises(ChromeForTestingError, match="SHA-256 mismatch"):
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
    assert resolve_chrome_for_testing(
        "145.0.1.2", home=home, cft_platform="mac-arm64"
    ).archive_sha256 == original.archive_sha256


def test_install_rejects_non_official_url_before_download(tmp_path):
    called = False

    def resolver(_version: str, *, cft_platform: str | None = None):
        return (
            "145.0.1.2",
            cft_platform or "mac-arm64",
            "https://example.invalid/chrome.zip",
        )

    def downloader(_url: str, _destination: Path):
        nonlocal called
        called = True

    with pytest.raises(ChromeForTestingError, match="official Google storage"):
        install_chrome_for_testing(
            "stable",
            home=tmp_path,
            cft_platform="mac-arm64",
            resolver=resolver,
            downloader=downloader,
        )
    assert not called


def test_safe_extract_rejects_path_traversal_and_special_files(tmp_path):
    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as bundle:
        bundle.writestr("../escape", "bad")

    with pytest.raises(ChromeForTestingError, match="Unsafe path"):
        safe_extract_chrome_for_testing_zip(traversal, tmp_path / "traversal-out")
    assert not (tmp_path / "escape").exists()

    special = tmp_path / "special.zip"
    with zipfile.ZipFile(special, "w") as bundle:
        item = zipfile.ZipInfo("device")
        item.external_attr = (stat.S_IFCHR | 0o600) << 16
        bundle.writestr(item, "bad")

    with pytest.raises(ChromeForTestingError, match="Unsupported file type"):
        safe_extract_chrome_for_testing_zip(special, tmp_path / "special-out")


def test_safe_extract_allows_internal_symlink_and_rejects_escape(tmp_path):
    internal = tmp_path / "internal.zip"
    with zipfile.ZipFile(internal, "w") as bundle:
        bundle.writestr("app/Versions/1/chrome", "binary")
        link = zipfile.ZipInfo("app/Versions/Current")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "1")

    destination = tmp_path / "internal-output"
    safe_extract_chrome_for_testing_zip(internal, destination)
    assert (destination / "app/Versions/Current").is_symlink()
    assert (destination / "app/Versions/Current/chrome").read_text() == "binary"

    escaping = tmp_path / "escaping.zip"
    with zipfile.ZipFile(escaping, "w") as bundle:
        link = zipfile.ZipInfo("app/escape")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "../../outside")

    with pytest.raises(ChromeForTestingError, match="Symlink escapes"):
        safe_extract_chrome_for_testing_zip(escaping, tmp_path / "escaping-output")


def test_remove_and_gc_are_scoped_to_cft_home(tmp_path):
    installation = _install(tmp_path)
    home = tmp_path / "chrome-for-testing"

    removed = remove_chrome_for_testing(
        installation.version,
        home=home,
        cft_platform=installation.platform,
    )
    assert removed == installation
    assert not installation.root_dir.exists()

    stale = home / "145.0.1.3" / ".mac-arm64-install-stale"
    stale.mkdir(parents=True)
    old = time.time() - 48 * 60 * 60
    os.utime(stale, (old, old))

    preview = garbage_collect_chrome_for_testing(
        home=home,
        dry_run=True,
        minimum_age_seconds=24 * 60 * 60,
    )
    assert preview["candidates"] == [str(stale)]
    assert stale.exists()

    with pytest.raises(ChromeForTestingError, match="without yes=True"):
        garbage_collect_chrome_for_testing(
            home=home,
            dry_run=False,
            minimum_age_seconds=24 * 60 * 60,
        )

    applied = garbage_collect_chrome_for_testing(
        home=home,
        dry_run=False,
        yes=True,
        minimum_age_seconds=24 * 60 * 60,
    )
    assert applied["removed"] == [str(stale)]
    assert not stale.exists()


def test_cft_install_json_output_is_machine_readable(monkeypatch, tmp_path):
    installation = ChromeForTestingInstallation(
        kind="chrome-for-testing",
        version="145.0.1.2",
        platform="mac-arm64",
        root_dir=tmp_path / "installation",
        binary_path=tmp_path / "installation" / "chrome",
        source_url="https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
        archive_sha256="a" * 64,
        installed_at="2026-08-04T00:00:00+00:00",
    )
    installation.binary_path.parent.mkdir(parents=True)
    installation.binary_path.write_text("chrome")
    monkeypatch.setattr(public_api, "install", lambda *args, **kwargs: installation)
    monkeypatch.setattr(
        public_api,
        "doctor",
        lambda *_args, **_kwargs: {
            **installation.to_dict(),
            "status": "ready",
            "reported_version": "Google Chrome for Testing 145.0.1.2",
            "errors": [],
        },
    )

    result = CliRunner().invoke(
        main,
        [
            "chrome-for-testing",
            "install",
            "--version",
            "145.0.1.2",
            "--output",
            "json",
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["binary_path"] == str(installation.binary_path)
    assert payload["status"] == "ready"


def test_cft_cli_uses_chatstyle_auto_prompt_policy(monkeypatch, tmp_path):
    import chatstyle.core.interactive as interactive_module
    import chatstyle.tui.prompt as prompt_module

    monkeypatch.setattr(interactive_module, "is_interactive_available", lambda: True)
    monkeypatch.setattr(
        prompt_module,
        "ask_text",
        lambda *args, **kwargs: pytest.fail("automatic prompt should be disabled"),
    )

    result = CliRunner().invoke(
        main,
        ["chrome-for-testing", "show", "--home", str(tmp_path)],
        env={"CHATARCH_AUTO_PROMPT": "off"},
    )

    assert result.exit_code != 0
    assert "Missing required value: version" in result.output


def test_cft_cli_explicit_interactive_prompts_missing_version(monkeypatch, tmp_path):
    import chatstyle.core.interactive as interactive_module
    import chatstyle.tui.prompt as prompt_module

    installation = ChromeForTestingInstallation(
        kind="chrome-for-testing",
        version="145.0.1.2",
        platform="mac-arm64",
        root_dir=tmp_path,
        binary_path=tmp_path / "chrome",
        source_url="https://storage.googleapis.com/chrome-for-testing-public/chrome.zip",
        archive_sha256="a" * 64,
        installed_at="2026-08-04T00:00:00+00:00",
    )
    monkeypatch.setattr(interactive_module, "is_interactive_available", lambda: True)
    monkeypatch.setattr(prompt_module, "ask_text", lambda *args, **kwargs: "145.0.1.2")
    monkeypatch.setattr(public_api, "resolve", lambda *args, **kwargs: installation)

    result = CliRunner().invoke(
        main,
        ["chrome-for-testing", "show", "--home", str(tmp_path), "-i"],
        env={"CHATARCH_AUTO_PROMPT": "off"},
    )

    assert result.exit_code == 0, result.output
    assert "145.0.1.2" in result.output


def test_cft_remove_requires_yes():
    result = CliRunner().invoke(
        main,
        ["chrome-for-testing", "remove", "145.0.1.2", "-I"],
    )

    assert result.exit_code != 0
    assert "Refusing to remove without --yes" in result.output
