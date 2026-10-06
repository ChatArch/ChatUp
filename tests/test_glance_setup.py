import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from chatup.cli import main


TAG = "chatarch-v0.2.1"
SOURCE_SHA = "a" * 40
VERSION = f"{TAG}+{SOURCE_SHA}"
ARCHIVE = f"glance-{TAG}-linux-amd64.tar.gz"


def _release_files(archive: bytes = b"archive", **overrides):
    fields = {
        "tag": TAG,
        "source_sha": SOURCE_SHA,
        "binary_version": VERSION,
        "archive": ARCHIVE,
        "goos": "linux",
        "goarch": "amd64",
        "cgo_enabled": "0",
    }
    fields.update(overrides)
    buildinfo = "".join(f"{key}={value}\n" for key, value in fields.items()).encode()
    sums = (
        f"{hashlib.sha256(archive).hexdigest()}  {ARCHIVE}\n"
        f"{hashlib.sha256(buildinfo).hexdigest()}  BUILDINFO.txt\n"
    ).encode()
    return {ARCHIVE: archive, "BUILDINFO.txt": buildinfo, "SHA256SUMS": sums}


def _fake_download(files, requested):
    def download(url, destination):
        name = url.rsplit("/", 1)[-1]
        requested.append(name)
        destination.write_bytes(files[name])

    return download


def test_glance_command_exists_and_bare_invocation_dispatches(monkeypatch, tmp_path):
    import chatup.setup.elements as elements

    called = []
    monkeypatch.setattr(elements, "setup_glance", lambda **kwargs: called.append(kwargs) or {})

    result = CliRunner().invoke(main, ["glance", "--runtime-home", str(tmp_path), "-I"])

    assert result.exit_code == 0, result.output
    assert called == [{
        "version": "latest", "runtime_home": tmp_path, "dry_run": False, "interactive": False,
    }]


def test_glance_installer_has_importable_api_and_strict_version():
    from chatup.setup.glance import install_glance, normalize_release_tag

    assert callable(install_glance)
    assert normalize_release_tag(TAG) == TAG
    for invalid in ("v0.2.1", "0.2.1", "chatarch-v1.2", "chatarch-v01.2.3", "chatarch-v1.2.3+abc"):
        with pytest.raises(ValueError, match="chatarch-vMAJOR.MINOR.PATCH"):
            normalize_release_tag(invalid)


def test_glance_rejects_unsupported_platform_before_download_or_write(monkeypatch, tmp_path):
    import chatup.setup.glance as glance

    requested = []
    monkeypatch.setattr(glance.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(glance.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(glance, "download_release_asset", lambda *args: requested.append(args))
    with pytest.raises(ValueError, match="Linux amd64"):
        glance.install_glance(version=TAG, home=tmp_path / "runtime")
    assert requested == []
    assert not (tmp_path / "runtime").exists()


@pytest.mark.parametrize(("files", "message"), [
    ({**_release_files(), "SHA256SUMS": (f"{'0' * 64}  {ARCHIVE}\n" f"{'0' * 64}  BUILDINFO.txt\n").encode()}, "SHA256 mismatch"),
    (_release_files(source_sha="b" * 39), "source_sha"),
    (_release_files(tag="chatarch-v0.2.0"), "tag"),
    (_release_files(binary_version="chatarch-v0.2.1+" + "b" * 40), "binary_version"),
])
def test_glance_rejects_hash_or_buildinfo_mismatch_before_runtime_write(monkeypatch, tmp_path, files, message):
    import chatup.setup.glance as glance

    requested = []
    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(glance, "download_release_asset", _fake_download(files, requested))
    with pytest.raises(ValueError, match=message):
        glance.install_glance(version=TAG, home=tmp_path / "runtime")
    assert requested == [ARCHIVE, "SHA256SUMS", "BUILDINFO.txt"]
    assert not (tmp_path / "runtime").exists()


def test_hostile_archive_is_rejected_by_chatglance_portable_api(monkeypatch, tmp_path):
    import chatup.setup.glance as glance

    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        payload = b"hostile"
        member = tarfile.TarInfo("../outside")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    files = _release_files(stream.getvalue())
    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "amd64")
    monkeypatch.setattr(glance, "download_release_asset", _fake_download(files, []))
    with pytest.raises(ValueError, match="only a regular glance executable"):
        glance.install_glance(version=TAG, home=tmp_path / "runtime")
    assert not (tmp_path / "outside").exists()
    assert not (tmp_path / "runtime").exists()


def test_install_is_idempotent_and_preserves_existing_config(monkeypatch, tmp_path):
    import chatup.setup.glance as glance

    archive_bytes = b"reviewed archive"
    files = _release_files(archive_bytes)
    requested = []
    home = tmp_path / "runtime"
    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "amd64")
    monkeypatch.setattr(glance, "download_release_asset", _fake_download(files, requested))
    monkeypatch.setattr(glance, "_read_observed_version", lambda path: VERSION)

    def install_verified_binary(archive, sha256, runtime_home, *, version):
        binary = Path(runtime_home) / "bin/glance"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"binary")
        binary.chmod(0o755)
        provenance = {
            "source": "verified local archive", "source_tag": TAG, "source_revision": SOURCE_SHA,
            "version": VERSION, "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
            "binary_sha256": hashlib.sha256(b"binary").hexdigest(),
        }
        binary.with_name("glance.provenance.json").write_text(json.dumps(provenance))
        return binary

    def initialize(runtime_home):
        config = Path(runtime_home) / "config/glance.yml"
        config.parent.mkdir(parents=True, exist_ok=True)
        if not config.exists():
            config.write_text("server:\n  host: 127.0.0.1\n")
        return [config]

    monkeypatch.setattr(glance, "install_verified_binary", install_verified_binary)
    monkeypatch.setattr(glance, "initialize", initialize)
    first = glance.install_glance(version=TAG, home=home)
    config = home / "config/glance.yml"
    config.write_text(config.read_text() + "# user note\n")
    second = glance.install_glance(version=TAG, home=home)
    assert first.status == "installed"
    assert second.status == "reused"
    assert config.read_text().endswith("# user note\n")
    assert second.start_command == ("chatglance", "runtime", "serve", "--runtime-home", str(home))
    assert requested == [ARCHIVE, "SHA256SUMS", "BUILDINFO.txt"] * 2


def test_existing_unverified_runtime_is_never_replaced(monkeypatch, tmp_path):
    import chatup.setup.glance as glance

    home = tmp_path / "runtime"
    (home / "bin").mkdir(parents=True)
    (home / "bin/glance").write_text("user binary")
    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "amd64")
    monkeypatch.setattr(glance, "download_release_asset", _fake_download(_release_files(), []))
    with pytest.raises(ValueError, match="chatglance runtime update"):
        glance.install_glance(version=TAG, home=home)
    assert (home / "bin/glance").read_text() == "user binary"


def test_dry_run_has_no_network_or_filesystem_side_effects(monkeypatch, tmp_path):
    import chatup.setup.glance as glance

    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "amd64")
    monkeypatch.setattr(glance, "download_release_asset", lambda *args: pytest.fail("downloaded"))
    result = glance.install_glance(version=TAG, home=tmp_path / "runtime", dry_run=True)
    assert result.status == "planned"
    assert result.tag == TAG
    assert not (tmp_path / "runtime").exists()
